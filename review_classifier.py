#!/usr/bin/env python3
"""
Система автоматической разметки отзывов с использованием локальной LLM
Поддерживает модели через Ollama или другие локальные API
"""

import json
import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import requests
from collections import Counter


@dataclass
class ReviewAnnotation:
    """Структура аннотации отзыва"""
    category: str
    subcategory: str
    tags: List[str]


class ReviewClassifier:
    """Классификатор отзывов с использованием локальной LLM"""
    
    def __init__(self, model_endpoint: str = "http://localhost:11434/api/generate", 
                 model_name: str = "llama3.2:3b"):
        self.model_endpoint = model_endpoint
        self.model_name = model_name
        self.categories = {}
        self.subcategories = {}
        self.tags = set()
        self.load_existing_annotations()
    
    def load_existing_annotations(self, filepath: str = "reviews.json"):
        """Загружает существующие аннотации для обучения"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Парсим объекты из файла
            objects = re.findall(r'\{[^}]*\}', content, re.DOTALL)
            
            categories = []
            subcategories = []
            all_tags = []
            
            for obj_str in objects:
                try:
                    obj = json.loads(obj_str)
                    if 'категория' in obj:
                        categories.append(obj['категория'])
                    if 'подкатегория' in obj:
                        subcategories.append(obj['подкатегория'])
                    if 'теги' in obj:
                        all_tags.extend(obj['теги'])
                except:
                    continue
            
            # Сохраняем статистику для промпта
            self.categories = dict(Counter(categories).most_common())
            self.subcategories = dict(Counter(subcategories).most_common())
            self.tags = set(all_tags)
            
            print(f"Загружено {len(categories)} размеченных отзывов")
            print(f"Категорий: {len(self.categories)}")
            print(f"Подкатегорий: {len(self.subcategories)}")
            print(f"Тегов: {len(self.tags)}")
            
        except Exception as e:
            print(f"Ошибка загрузки аннотаций: {e}")
    
    def create_classification_prompt(self, review_text: str) -> str:
        """Создает промпт для классификации отзыва"""
        
        categories_list = "\n".join([f"- {cat}" for cat in self.categories.keys()])
        subcategories_list = "\n".join([f"- {subcat}" for subcat in self.subcategories.keys()])
        tags_list = ", ".join(sorted(list(self.tags)))
        
        prompt = f"""Ты - эксперт по анализу отзывов о мобильном приложении и сервисе доставки продуктов.

Твоя задача: проанализировать отзыв и присвоить ему категорию, подкатегорию и теги на основе существующей схемы разметки.

СУЩЕСТВУЮЩИЕ КАТЕГОРИИ:
{categories_list}

СУЩЕСТВУЮЩИЕ ПОДКАТЕГОРИИ:
{subcategories_list}

СУЩЕСТВУЮЩИЕ ТЕГИ:
{tags_list}

ПРАВИЛА РАЗМЕТКИ:
1. Выбери ОДНУ наиболее подходящую категорию из списка выше
2. Выбери ОДНУ наиболее подходящую подкатегорию из списка выше
3. Выбери 1-6 наиболее релевантных тегов из списка выше
4. Если отзыв не подходит ни под одну категорию, используй "Общие и прочие отзывы"
5. Теги должны отражать ключевые аспекты отзыва

ОТЗЫВ ДЛЯ АНАЛИЗА:
"{review_text}"

ОТВЕТ ДОЛЖЕН БЫТЬ СТРОГО В ФОРМАТЕ JSON:
{{
    "категория": "название_категории",
    "подкатегория": "название_подкатегории", 
    "теги": ["тег1", "тег2", "тег3"]
}}

Отвечай только JSON, без дополнительных комментариев."""

        return prompt
    
    def query_llm(self, prompt: str) -> Optional[str]:
        """Отправляет запрос к локальной LLM"""
        try:
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "num_predict": 200
                }
            }
            
            response = requests.post(self.model_endpoint, json=payload, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            return result.get('response', '').strip()
            
        except Exception as e:
            print(f"Ошибка запроса к LLM: {e}")
            return None
    
    def parse_llm_response(self, response: str) -> Optional[ReviewAnnotation]:
        """Парсит ответ LLM и извлекает аннотации"""
        try:
            # Ищем JSON в ответе
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                return None
            
            json_str = json_match.group()
            data = json.loads(json_str)
            
            category = data.get('категория', '')
            subcategory = data.get('подкатегория', '')
            tags = data.get('теги', [])
            
            # Валидация
            if category not in self.categories:
                category = "Общие и прочие отзывы"
            
            if subcategory not in self.subcategories:
                # Пытаемся найти подходящую подкатегорию для категории
                if category == "Общие и прочие отзывы":
                    subcategory = "Положительный общий отзыв"
                else:
                    subcategory = list(self.subcategories.keys())[0]
            
            # Фильтруем теги
            valid_tags = [tag for tag in tags if tag in self.tags]
            if not valid_tags:
                valid_tags = ["общий"]
            
            return ReviewAnnotation(
                category=category,
                subcategory=subcategory,
                tags=valid_tags
            )
            
        except Exception as e:
            print(f"Ошибка парсинга ответа: {e}")
            return None
    
    def classify_review(self, review_text: str) -> Optional[ReviewAnnotation]:
        """Классифицирует один отзыв"""
        prompt = self.create_classification_prompt(review_text)
        response = self.query_llm(prompt)
        
        if response:
            return self.parse_llm_response(response)
        return None
    
    def classify_reviews_batch(self, reviews: List[str]) -> List[Optional[ReviewAnnotation]]:
        """Классифицирует список отзывов"""
        results = []
        for i, review in enumerate(reviews):
            print(f"Обрабатываю отзыв {i+1}/{len(reviews)}")
            result = self.classify_review(review)
            results.append(result)
        return results
    
    def save_annotated_reviews(self, reviews: List[str], annotations: List[ReviewAnnotation], 
                             output_file: str = "new_reviews_annotated.json"):
        """Сохраняет размеченные отзывы в файл"""
        annotated_data = []
        
        for review, annotation in zip(reviews, annotations):
            if annotation:
                item = {
                    "отзыв": review,
                    "категория": annotation.category,
                    "подкатегория": annotation.subcategory,
                    "теги": annotation.tags
                }
                annotated_data.append(item)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(annotated_data, f, ensure_ascii=False, indent=2)
        
        print(f"Сохранено {len(annotated_data)} размеченных отзывов в {output_file}")


def main():
    """Пример использования"""
    # Инициализация классификатора
    classifier = ReviewClassifier()
    
    # Примеры новых отзывов для разметки
    new_reviews = [
        "Приложение тормозит и постоянно выдает ошибки при оформлении заказа",
        "Отличная доставка, все привезли быстро и качественно!",
        "Не могу найти нужный товар в каталоге, поиск работает плохо",
        "Бонусы списались, но скидка не применилась на кассе",
        "Поддержка не отвечает уже неделю на мое обращение"
    ]
    
    print("Начинаю классификацию новых отзывов...")
    annotations = classifier.classify_reviews_batch(new_reviews)
    
    # Показываем результаты
    for review, annotation in zip(new_reviews, annotations):
        print(f"\nОтзыв: {review}")
        if annotation:
            print(f"Категория: {annotation.category}")
            print(f"Подкатегория: {annotation.subcategory}")
            print(f"Теги: {', '.join(annotation.tags)}")
        else:
            print("Не удалось классифицировать")
    
    # Сохраняем результаты
    valid_annotations = [ann for ann in annotations if ann is not None]
    valid_reviews = [rev for rev, ann in zip(new_reviews, annotations) if ann is not None]
    
    if valid_annotations:
        classifier.save_annotated_reviews(valid_reviews, valid_annotations)


if __name__ == "__main__":
    main()