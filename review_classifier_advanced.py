#!/usr/bin/env python3
"""
Улучшенная система автоматической разметки отзывов
Поддерживает множественные провайдеры LLM и дополнительные функции
"""

import json
import re
import argparse
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path
from collections import Counter
import time

# Импортируем наши провайдеры
from alternative_llm_configs import create_llm_provider, find_working_provider, LLMProvider


@dataclass
class ReviewAnnotation:
    """Структура аннотации отзыва"""
    category: str
    subcategory: str
    tags: List[str]
    confidence: float = 1.0


class AdvancedReviewClassifier:
    """Продвинутый классификатор отзывов с поддержкой множественных провайдеров"""
    
    def __init__(self, provider_name: str = None, **provider_kwargs):
        self.provider = None
        self.categories = {}
        self.subcategories = {}
        self.tags = set()
        self.category_examples = {}
        
        # Инициализация провайдера
        if provider_name:
            self.provider = create_llm_provider(provider_name, **provider_kwargs)
        else:
            self.provider = find_working_provider()
        
        if not self.provider:
            raise RuntimeError("Не удалось инициализировать ни один провайдер LLM")
        
        self.load_existing_annotations()
    
    def load_existing_annotations(self, filepath: str = "reviews.json"):
        """Загружает существующие аннотации и создает примеры для каждой категории"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Парсим объекты из файла
            objects = re.findall(r'\{[^}]*\}', content, re.DOTALL)
            
            categories = []
            subcategories = []
            all_tags = []
            examples_by_category = {}
            
            for obj_str in objects:
                try:
                    obj = json.loads(obj_str)
                    if 'категория' in obj and 'отзыв' in obj:
                        category = obj['категория']
                        review_text = obj['отзыв']
                        
                        categories.append(category)
                        
                        if category not in examples_by_category:
                            examples_by_category[category] = []
                        
                        # Сохраняем до 3 примеров для каждой категории
                        if len(examples_by_category[category]) < 3:
                            examples_by_category[category].append({
                                'review': review_text[:200] + '...' if len(review_text) > 200 else review_text,
                                'subcategory': obj.get('подкатегория', ''),
                                'tags': obj.get('теги', [])
                            })
                    
                    if 'подкатегория' in obj:
                        subcategories.append(obj['подкатегория'])
                    if 'теги' in obj:
                        all_tags.extend(obj['теги'])
                except:
                    continue
            
            # Сохраняем статистику
            self.categories = dict(Counter(categories).most_common())
            self.subcategories = dict(Counter(subcategories).most_common())
            self.tags = set(all_tags)
            self.category_examples = examples_by_category
            
            print(f"Загружено {len(categories)} размеченных отзывов")
            print(f"Категорий: {len(self.categories)}")
            print(f"Подкатегорий: {len(self.subcategories)}")
            print(f"Тегов: {len(self.tags)}")
            
        except Exception as e:
            print(f"Ошибка загрузки аннотаций: {e}")
    
    def create_enhanced_prompt(self, review_text: str) -> str:
        """Создает улучшенный промпт с примерами для каждой категории"""
        
        # Создаем описание категорий с примерами
        categories_with_examples = []
        for category, count in self.categories.items():
            examples = self.category_examples.get(category, [])
            examples_text = ""
            
            if examples:
                examples_text = "\nПримеры отзывов этой категории:\n"
                for i, example in enumerate(examples[:2], 1):
                    examples_text += f"{i}. \"{example['review']}\"\n"
            
            categories_with_examples.append(f"- {category} ({count} отзывов){examples_text}")
        
        categories_section = "\n".join(categories_with_examples)
        
        # Топ подкатегории
        top_subcategories = list(self.subcategories.keys())[:15]
        subcategories_list = "\n".join([f"- {subcat}" for subcat in top_subcategories])
        
        # Топ теги
        tag_counts = Counter()
        for obj_str in re.findall(r'\{[^}]*\}', open('reviews.json', 'r', encoding='utf-8').read(), re.DOTALL):
            try:
                obj = json.loads(obj_str)
                if 'теги' in obj:
                    for tag in obj['теги']:
                        tag_counts[tag] += 1
            except:
                continue
        
        top_tags = [tag for tag, _ in tag_counts.most_common(30)]
        tags_list = ", ".join(top_tags)
        
        prompt = f"""Ты - эксперт по анализу отзывов о мобильном приложении и сервисе доставки продуктов.

Проанализируй отзыв и присвой ему наиболее подходящую категорию, подкатегорию и теги.

ДОСТУПНЫЕ КАТЕГОРИИ С ПРИМЕРАМИ:
{categories_section}

НАИБОЛЕЕ ЧАСТЫЕ ПОДКАТЕГОРИИ:
{subcategories_list}

НАИБОЛЕЕ ЧАСТЫЕ ТЕГИ:
{tags_list}

ПРАВИЛА КЛАССИФИКАЦИИ:
1. Выбери ОДНУ наиболее подходящую категорию из списка выше
2. Выбери ОДНУ наиболее подходящую подкатегорию из списка выше  
3. Выбери 2-5 наиболее релевантных тегов из списка выше
4. Учитывай эмоциональный тон отзыва (позитивный/негативный)
5. Обращай внимание на конкретные проблемы или похвалы

ОТЗЫВ ДЛЯ АНАЛИЗА:
"{review_text}"

Ответь СТРОГО в формате JSON без дополнительного текста:
{{
    "категория": "точное_название_категории",
    "подкатегория": "точное_название_подкатегории",
    "теги": ["тег1", "тег2", "тег3"]
}}"""

        return prompt
    
    def classify_review_with_retry(self, review_text: str, max_retries: int = 3) -> Optional[ReviewAnnotation]:
        """Классифицирует отзыв с повторными попытками"""
        
        for attempt in range(max_retries):
            try:
                prompt = self.create_enhanced_prompt(review_text)
                response = self.provider.query(prompt, temperature=0.1, max_tokens=300)
                
                if response:
                    annotation = self.parse_llm_response(response)
                    if annotation:
                        return annotation
                
                print(f"Попытка {attempt + 1} не удалась, повторяю...")
                time.sleep(1)
                
            except Exception as e:
                print(f"Ошибка на попытке {attempt + 1}: {e}")
                time.sleep(1)
        
        print(f"Не удалось классифицировать отзыв после {max_retries} попыток")
        return None
    
    def parse_llm_response(self, response: str) -> Optional[ReviewAnnotation]:
        """Улучшенный парсинг ответа LLM"""
        try:
            # Очищаем ответ от лишнего текста
            response = response.strip()
            
            # Ищем JSON в ответе
            json_matches = re.findall(r'\{[^{}]*\}', response, re.DOTALL)
            
            for json_str in json_matches:
                try:
                    data = json.loads(json_str)
                    
                    category = data.get('категория', '').strip()
                    subcategory = data.get('подкатегория', '').strip()
                    tags = data.get('теги', [])
                    
                    # Валидация и коррекция категории
                    if category not in self.categories:
                        # Пытаемся найти похожую категорию
                        category = self.find_similar_category(category)
                    
                    # Валидация и коррекция подкатегории
                    if subcategory not in self.subcategories:
                        subcategory = self.find_similar_subcategory(subcategory, category)
                    
                    # Валидация тегов
                    valid_tags = []
                    for tag in tags:
                        if isinstance(tag, str):
                            tag = tag.strip()
                            if tag in self.tags:
                                valid_tags.append(tag)
                            else:
                                # Пытаемся найти похожий тег
                                similar_tag = self.find_similar_tag(tag)
                                if similar_tag:
                                    valid_tags.append(similar_tag)
                    
                    # Если не нашли подходящих тегов, добавляем базовые
                    if not valid_tags:
                        if any(word in category.lower() for word in ['положительный', 'отличн', 'хорош']):
                            valid_tags = ['позитив']
                        else:
                            valid_tags = ['негатив']
                    
                    return ReviewAnnotation(
                        category=category,
                        subcategory=subcategory,
                        tags=valid_tags[:5]  # Ограничиваем количество тегов
                    )
                    
                except json.JSONDecodeError:
                    continue
            
            return None
            
        except Exception as e:
            print(f"Ошибка парсинга ответа: {e}")
            return None
    
    def find_similar_category(self, category: str) -> str:
        """Находит наиболее похожую категорию"""
        category_lower = category.lower()
        
        # Простое сопоставление по ключевым словам
        if any(word in category_lower for word in ['проблем', 'ошибк', 'сбой', 'не работ']):
            return "Проблемы в работе приложения"
        elif any(word in category_lower for word in ['доставк', 'курьер', 'заказ']):
            return "Качество сервиса доставки"
        elif any(word in category_lower for word in ['бонус', 'акци', 'скидк', 'лояльност']):
            return "Программа лояльности и акции"
        elif any(word in category_lower for word in ['поддержк', 'помощ']):
            return "Работа службы поддержки"
        else:
            return "Общие и прочие отзывы"
    
    def find_similar_subcategory(self, subcategory: str, category: str) -> str:
        """Находит подходящую подкатегорию для категории"""
        subcategory_lower = subcategory.lower()
        
        # Подбираем подкатегорию в зависимости от категории
        if category == "Проблемы в работе приложения":
            if any(word in subcategory_lower for word in ['интерфейс', 'ui', 'ux', 'неудобн']):
                return "Проблемы с интерфейсом (UI/UX)"
            elif any(word in subcategory_lower for word in ['авториз', 'вход', 'логин']):
                return "Проблема с авторизацией/входом"
            elif any(word in subcategory_lower for word in ['оплат', 'платеж']):
                return "Проблемы с оплатой"
            else:
                return "Технические сбои и ошибки"
        
        elif category == "Качество сервиса доставки":
            if any(word in subcategory_lower for word in ['качеств', 'товар', 'продукт']):
                return "Проблемы с качеством товаров"
            elif any(word in subcategory_lower for word in ['состав', 'комплект', 'забыли']):
                return "Проблемы с составом заказа"
            elif any(word in subcategory_lower for word in ['время', 'опоздал', 'долго']):
                return "Длительное ожидание доставки"
            elif any(word in subcategory_lower for word in ['позитив', 'хорош', 'отличн']):
                return "Положительный отзыв о доставке"
            else:
                return "Отмена заказа"
        
        elif category == "Общие и прочие отзывы":
            if any(word in subcategory_lower for word in ['позитив', 'хорош', 'отличн', 'спасиб']):
                return "Положительный общий отзыв"
            elif any(word in subcategory_lower for word in ['предложен', 'улучшен', 'добавьт']):
                return "Предложения по улучшению"
            elif any(word in subcategory_lower for word in ['конкурент', 'сравнен']):
                return "Сравнение с конкурентами"
            else:
                return "Негативный общий отзыв"
        
        # Возвращаем наиболее частую подкатегорию как fallback
        return list(self.subcategories.keys())[0]
    
    def find_similar_tag(self, tag: str) -> Optional[str]:
        """Находит похожий тег из существующих"""
        tag_lower = tag.lower()
        
        # Простое сопоставление
        for existing_tag in self.tags:
            if tag_lower in existing_tag.lower() or existing_tag.lower() in tag_lower:
                return existing_tag
        
        return None
    
    def classify_reviews_from_file(self, input_file: str, output_file: str = None) -> List[Dict]:
        """Классифицирует отзывы из файла"""
        
        # Читаем новые отзывы
        reviews = []
        if input_file.endswith('.json'):
            with open(input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    reviews = [item.get('отзыв', item) if isinstance(item, dict) else str(item) for item in data]
                else:
                    reviews = [str(data)]
        else:
            # Текстовый файл - каждая строка отзыв
            with open(input_file, 'r', encoding='utf-8') as f:
                reviews = [line.strip() for line in f if line.strip()]
        
        print(f"Загружено {len(reviews)} отзывов для классификации")
        
        # Классифицируем
        results = []
        for i, review in enumerate(reviews):
            print(f"Обрабатываю отзыв {i+1}/{len(reviews)}")
            
            annotation = self.classify_review_with_retry(review)
            
            if annotation:
                result = {
                    "отзыв": review,
                    "категория": annotation.category,
                    "подкатегория": annotation.subcategory,
                    "теги": annotation.tags
                }
                results.append(result)
                
                print(f"✓ Категория: {annotation.category}")
                print(f"  Подкатегория: {annotation.subcategory}")
                print(f"  Теги: {', '.join(annotation.tags)}")
            else:
                print("✗ Не удалось классифицировать")
            
            print("-" * 50)
        
        # Сохраняем результаты
        if output_file is None:
            output_file = f"classified_{Path(input_file).stem}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\n✓ Сохранено {len(results)} классифицированных отзывов в {output_file}")
        
        return results
    
    def get_classification_stats(self, results: List[Dict]) -> Dict:
        """Возвращает статистику классификации"""
        categories = [r['категория'] for r in results]
        subcategories = [r['подкатегория'] for r in results]
        all_tags = []
        for r in results:
            all_tags.extend(r['теги'])
        
        return {
            'total_reviews': len(results),
            'categories': dict(Counter(categories)),
            'subcategories': dict(Counter(subcategories)),
            'tags': dict(Counter(all_tags))
        }


def main():
    """Основная функция с аргументами командной строки"""
    parser = argparse.ArgumentParser(description='Система автоматической разметки отзывов')
    parser.add_argument('input_file', help='Файл с неразмеченными отзывами')
    parser.add_argument('-o', '--output', help='Выходной файл (по умолчанию: classified_<input>.json)')
    parser.add_argument('-p', '--provider', default='ollama', 
                       choices=['ollama', 'lm_studio', 'text_gen_webui', 'localai', 'llamafile'],
                       help='Провайдер LLM (по умолчанию: ollama)')
    parser.add_argument('--model', help='Название модели для провайдера')
    parser.add_argument('--url', help='URL для API провайдера')
    
    args = parser.parse_args()
    
    # Подготавливаем параметры провайдера
    provider_kwargs = {}
    if args.model:
        provider_kwargs['model'] = args.model
    if args.url:
        provider_kwargs['base_url'] = args.url
    
    try:
        # Инициализируем классификатор
        print(f"Инициализация классификатора с провайдером: {args.provider}")
        classifier = AdvancedReviewClassifier(args.provider, **provider_kwargs)
        
        # Классифицируем отзывы
        results = classifier.classify_reviews_from_file(args.input_file, args.output)
        
        # Показываем статистику
        stats = classifier.get_classification_stats(results)
        print(f"\n=== СТАТИСТИКА КЛАССИФИКАЦИИ ===")
        print(f"Всего отзывов: {stats['total_reviews']}")
        print(f"\nКатегории:")
        for cat, count in stats['categories'].items():
            print(f"  {cat}: {count}")
        
        print(f"\nТоп-5 тегов:")
        for tag, count in Counter(stats['tags']).most_common(5):
            print(f"  {tag}: {count}")
            
    except Exception as e:
        print(f"Ошибка: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())