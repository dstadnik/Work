#!/usr/bin/env python3
"""
🚀 Система автоматической разметки отзывов для JupyterHub
Простая в использовании версия для интерактивной работы
"""

import json
import re
import requests
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
from typing import Dict, List, Optional
from dataclasses import dataclass
import time
import subprocess
import os

# Настройка отображения
plt.style.use('default')
sns.set_palette("husl")

@dataclass
class ReviewAnnotation:
    """Структура аннотации отзыва"""
    category: str
    subcategory: str
    tags: List[str]
    confidence: float = 1.0

class JupyterReviewClassifier:
    """Упрощенный классификатор отзывов для Jupyter"""
    
    def __init__(self, model_name: str = "llama3.2:3b", base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.model_name = model_name
        self.categories = {}
        self.subcategories = {}
        self.tags = set()
        self.category_examples = {}
        
        print("🔄 Инициализация классификатора...")
        self.load_existing_annotations()
        
    def check_ollama_status(self) -> bool:
        """Проверяет статус Ollama"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [m['name'] for m in models]
                
                if self.model_name in model_names:
                    print(f"✅ Ollama работает, модель {self.model_name} доступна")
                    return True
                else:
                    print(f"❌ Модель {self.model_name} не найдена")
                    print(f"Доступные модели: {model_names}")
                    return False
            else:
                print(f"❌ Ollama не отвечает (статус: {response.status_code})")
                return False
        except Exception as e:
            print(f"❌ Ошибка подключения к Ollama: {e}")
            return False
    
    def install_ollama_instructions(self):
        """Показывает инструкции по установке Ollama"""
        print("\n📝 ИНСТРУКЦИИ ПО УСТАНОВКЕ OLLAMA:")
        print("=" * 50)
        print("1. Откройте терминал в JupyterHub")
        print("2. Выполните команды:")
        print("   curl -fsSL https://ollama.com/install.sh | sh")
        print("   export PATH='/usr/local/bin:$PATH'")
        print("   ollama serve &")
        print("   ollama pull llama3.2:3b")
        print("\n3. Перезапустите этот notebook")
        print("=" * 50)
    
    def load_existing_annotations(self, filepath: str = "reviews.json"):
        """Загружает существующие аннотации"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
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
                        
                        if len(examples_by_category[category]) < 2:
                            examples_by_category[category].append({
                                'review': review_text[:100] + '...' if len(review_text) > 100 else review_text,
                                'subcategory': obj.get('подкатегория', ''),
                                'tags': obj.get('теги', [])
                            })
                    
                    if 'подкатегория' in obj:
                        subcategories.append(obj['подкатегория'])
                    if 'теги' in obj:
                        all_tags.extend(obj['теги'])
                except:
                    continue
            
            self.categories = dict(Counter(categories).most_common())
            self.subcategories = dict(Counter(subcategories).most_common())
            self.tags = set(all_tags)
            self.category_examples = examples_by_category
            
            print(f"📊 Загружено {len(categories)} размеченных отзывов")
            print(f"📂 Категорий: {len(self.categories)}")
            print(f"📋 Подкатегорий: {len(self.subcategories)}")
            print(f"🏷️ Тегов: {len(self.tags)}")
            
        except Exception as e:
            print(f"❌ Ошибка загрузки аннотаций: {e}")
    
    def create_prompt(self, review_text: str) -> str:
        """Создает промпт для классификации"""
        categories_list = "\n".join([f"- {cat}" for cat in list(self.categories.keys())[:5]])
        subcategories_list = "\n".join([f"- {subcat}" for subcat in list(self.subcategories.keys())[:10]])
        tags_list = ", ".join(sorted(list(self.tags))[:20])
        
        prompt = f"""Ты - эксперт по анализу отзывов о мобильном приложении и сервисе доставки.

Проанализируй отзыв и присвой ему категорию, подкатегорию и теги.

КАТЕГОРИИ:
{categories_list}

ПОДКАТЕГОРИИ:
{subcategories_list}

ТЕГИ:
{tags_list}

ОТЗЫВ: "{review_text}"

Ответь СТРОГО в формате JSON:
{{
    "категория": "название_категории",
    "подкатегория": "название_подкатегории",
    "теги": ["тег1", "тег2"]
}}"""
        
        return prompt
    
    def query_llm(self, prompt: str) -> Optional[str]:
        """Отправляет запрос к Ollama"""
        try:
            url = f"{self.base_url}/api/generate"
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
            
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            return result.get('response', '').strip()
            
        except Exception as e:
            print(f"❌ Ошибка запроса к LLM: {e}")
            return None
    
    def parse_response(self, response: str) -> Optional[ReviewAnnotation]:
        """Парсит ответ LLM"""
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                return None
            
            data = json.loads(json_match.group())
            
            category = data.get('категория', '').strip()
            subcategory = data.get('подкатегория', '').strip()
            tags = data.get('теги', [])
            
            # Валидация
            if category not in self.categories:
                category = "Общие и прочие отзывы"
            
            if subcategory not in self.subcategories:
                subcategory = "Положительный общий отзыв"
            
            valid_tags = [tag for tag in tags if tag in self.tags][:4]
            if not valid_tags:
                valid_tags = ["общий"]
            
            return ReviewAnnotation(
                category=category,
                subcategory=subcategory,
                tags=valid_tags
            )
            
        except Exception as e:
            print(f"❌ Ошибка парсинга: {e}")
            return None
    
    def classify_review(self, review_text: str) -> Optional[ReviewAnnotation]:
        """Классифицирует один отзыв"""
        if not self.check_ollama_status():
            return None
            
        prompt = self.create_prompt(review_text)
        response = self.query_llm(prompt)
        
        if response:
            return self.parse_response(response)
        return None
    
    def display_classification(self, review_text: str, annotation: ReviewAnnotation):
        """Красиво отображает результат классификации"""
        print("=" * 60)
        print(f"📝 ОТЗЫВ: {review_text}")
        print("=" * 60)
        print(f"📂 Категория: {annotation.category}")
        print(f"📋 Подкатегория: {annotation.subcategory}")
        print(f"🏷️ Теги: {', '.join(annotation.tags)}")
        print("=" * 60)
    
    def classify_interactive(self):
        """Интерактивная классификация отзыва"""
        print("✍️ Введите отзыв для классификации (или 'quit' для выхода):")
        
        while True:
            review_text = input("\n📝 Отзыв: ").strip()
            
            if review_text.lower() in ['quit', 'exit', 'выход']:
                print("👋 До свидания!")
                break
            
            if not review_text:
                print("❌ Пустой отзыв!")
                continue
            
            print("\n⏳ Классифицирую...")
            start_time = time.time()
            
            annotation = self.classify_review(review_text)
            end_time = time.time()
            
            if annotation:
                self.display_classification(review_text, annotation)
                print(f"⏱️ Время обработки: {end_time - start_time:.1f} сек")
            else:
                print("❌ Не удалось классифицировать отзыв")
            
            print("\n" + "-" * 60)
    
    def classify_batch(self, reviews_list: List[str], show_progress: bool = True) -> List[Dict]:
        """Пакетная классификация отзывов"""
        results = []
        
        if show_progress:
            print(f"📦 Начинаю обработку {len(reviews_list)} отзывов...")
        
        for i, review in enumerate(reviews_list, 1):
            if show_progress:
                print(f"⏳ Обрабатываю {i}/{len(reviews_list)}: {review[:50]}...")
            
            annotation = self.classify_review(review)
            
            if annotation:
                result = {
                    "отзыв": review,
                    "категория": annotation.category,
                    "подкатегория": annotation.subcategory,
                    "теги": annotation.tags
                }
                results.append(result)
                
                if show_progress:
                    print(f"✅ {annotation.category}")
            else:
                if show_progress:
                    print("❌ Ошибка классификации")
        
        return results
    
    def analyze_results(self, results: List[Dict]):
        """Анализирует и визуализирует результаты"""
        if not results:
            print("❌ Нет результатов для анализа")
            return
        
        df = pd.DataFrame(results)
        
        print("📊 СТАТИСТИКА КЛАССИФИКАЦИИ")
        print("=" * 40)
        print(f"Всего отзывов: {len(df)}")
        
        # Распределение по категориям
        print("\n📂 По категориям:")
        for cat, count in df['категория'].value_counts().items():
            print(f"  • {cat}: {count}")
        
        # Топ тегов
        all_tags = []
        for tags_list in df['теги']:
            all_tags.extend(tags_list)
        
        print("\n🏷️ Топ-5 тегов:")
        for tag, count in Counter(all_tags).most_common(5):
            print(f"  • {tag}: {count}")
        
        # Визуализация
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # График категорий
        df['категория'].value_counts().plot(kind='bar', ax=ax1, color='skyblue')
        ax1.set_title('Распределение по категориям', fontweight='bold')
        ax1.tick_params(axis='x', rotation=45)
        
        # График тегов
        top_tags = dict(Counter(all_tags).most_common(5))
        ax2.bar(top_tags.keys(), top_tags.values(), color='lightcoral')
        ax2.set_title('Топ-5 тегов', fontweight='bold')
        ax2.tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        plt.show()
    
    def save_results(self, results: List[Dict], filename_base: str = "classified_reviews"):
        """Сохраняет результаты в файлы"""
        if not results:
            print("❌ Нет результатов для сохранения")
            return
        
        # JSON
        json_file = f"{filename_base}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        # CSV
        df = pd.DataFrame(results)
        df['теги_строка'] = df['теги'].apply(lambda x: ', '.join(x))
        csv_file = f"{filename_base}.csv"
        df[['отзыв', 'категория', 'подкатегория', 'теги_строка']].to_csv(
            csv_file, index=False, encoding='utf-8'
        )
        
        print(f"💾 Результаты сохранены:")
        print(f"  • JSON: {json_file}")
        print(f"  • CSV: {csv_file}")
    
    def show_stats(self):
        """Показывает статистику существующих данных"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # График категорий
        categories_df = pd.DataFrame(list(self.categories.items()), 
                                   columns=['Категория', 'Количество'])
        categories_df = categories_df.sort_values('Количество', ascending=True)
        
        ax1.barh(categories_df['Категория'], categories_df['Количество'])
        ax1.set_title('Распределение по категориям', fontweight='bold')
        ax1.set_xlabel('Количество отзывов')
        
        # График подкатегорий
        top_subcats = dict(Counter(self.subcategories).most_common(8))
        subcats_df = pd.DataFrame(list(top_subcats.items()), 
                                 columns=['Подкатегория', 'Количество'])
        subcats_df = subcats_df.sort_values('Количество', ascending=True)
        
        ax2.barh(subcats_df['Подкатегория'], subcats_df['Количество'])
        ax2.set_title('Топ-8 подкатегорий', fontweight='bold')
        ax2.set_xlabel('Количество отзывов')
        
        plt.tight_layout()
        plt.show()


def main():
    """Основная функция для демонстрации"""
    print("🚀 СИСТЕМА АВТОМАТИЧЕСКОЙ РАЗМЕТКИ ОТЗЫВОВ")
    print("=" * 50)
    
    # Инициализация
    classifier = JupyterReviewClassifier()
    
    # Проверка Ollama
    if not classifier.check_ollama_status():
        classifier.install_ollama_instructions()
        return
    
    # Показ статистики
    print("\n📊 Статистика существующих данных:")
    classifier.show_stats()
    
    # Тестовые отзывы
    test_reviews = [
        "Не могу войти в приложение, ошибка авторизации",
        "Отличная доставка, все быстро!",
        "Бонусы не начислились за покупку"
    ]
    
    print("\n🧪 Тестирование на примерах...")
    results = classifier.classify_batch(test_reviews)
    
    if results:
        print("\n📋 Результаты тестирования:")
        for result in results:
            print(f"\n📝 {result['отзыв']}")
            print(f"📂 {result['категория']}")
            print(f"📋 {result['подкатегория']}")
            print(f"🏷️ {', '.join(result['теги'])}")
        
        # Анализ и сохранение
        classifier.analyze_results(results)
        classifier.save_results(results, "test_results")
        
        print("\n🎉 Система готова к работе!")
        print("\nДля интерактивной работы используйте:")
        print("classifier.classify_interactive()")
    else:
        print("❌ Тестирование не удалось")


if __name__ == "__main__":
    main()