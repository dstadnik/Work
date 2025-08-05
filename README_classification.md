# Система автоматической разметки отзывов

Система для автоматической классификации отзывов о мобильном приложении и сервисе доставки с использованием локальных LLM.

## Возможности

- ✅ Автоматическая классификация отзывов по категориям, подкатегориям и тегам
- ✅ Поддержка множественных провайдеров LLM (Ollama, LM Studio, Text Generation WebUI, LocalAI, llamafile)
- ✅ Обучение на существующих размеченных данных
- ✅ Валидация и коррекция результатов классификации
- ✅ Пакетная обработка отзывов из файлов
- ✅ Статистика классификации
- ✅ Простая установка и настройка

## Структура существующей разметки

### Категории (5):
1. **Проблемы в работе приложения** (29 отзывов)
2. **Качество сервиса доставки** (17 отзывов) 
3. **Общие и прочие отзывы** (17 отзывов)
4. **Программа лояльности и акции** (10 отзывов)
5. **Работа службы поддержки** (7 отзывов)

### Основные подкатегории:
- Технические сбои и ошибки
- Проблемы с интерфейсом (UI/UX)
- Положительный общий отзыв
- Проблемы с составом заказа
- Проблема с авторизацией/входом
- И другие (всего 27 подкатегорий)

### Популярные теги:
- ui_ux, позитив, сбой, поддержка, бонусы, негатив, обновление, акции, и другие (всего 103 тега)

## Установка и настройка

### Вариант 1: Ollama (рекомендуется)

```bash
# Установка и настройка Ollama
chmod +x setup_ollama.sh
./setup_ollama.sh
```

Этот скрипт:
- Установит Ollama
- Запустит сервис
- Загрузит рекомендуемую модель llama3.2:3b
- Протестирует работу

### Вариант 2: Другие провайдеры

Система поддерживает несколько провайдеров:

1. **LM Studio** - удобный GUI для моделей
   - Скачайте с https://lmstudio.ai/
   - Загрузите модель и запустите сервер на порту 1234

2. **Text Generation WebUI** - много настроек, GPU поддержка
   ```bash
   git clone https://github.com/oobabooga/text-generation-webui
   cd text-generation-webui
   ./start_linux.sh --api
   ```

3. **LocalAI** - совместимый с OpenAI API
   ```bash
   docker run -p 8080:8080 --name local-ai -ti localai/localai:latest
   ```

4. **llamafile** - один исполняемый файл
   ```bash
   # Скачайте llamafile с https://github.com/Mozilla-Ocho/llamafile
   chmod +x llamafile
   ./llamafile --server --port 8080
   ```

### Проверка провайдеров

```bash
python3 alternative_llm_configs.py
```

## Использование

### Базовое использование

```bash
# Классификация отзывов из текстового файла
python3 review_classifier_advanced.py sample_new_reviews.txt

# Указание конкретного провайдера
python3 review_classifier_advanced.py sample_new_reviews.txt -p ollama

# Указание выходного файла
python3 review_classifier_advanced.py sample_new_reviews.txt -o my_results.json
```

### Расширенные опции

```bash
# Использование другой модели
python3 review_classifier_advanced.py reviews.txt --model llama3.2:1b

# Использование другого URL
python3 review_classifier_advanced.py reviews.txt --url http://192.168.1.100:11434

# LM Studio
python3 review_classifier_advanced.py reviews.txt -p lm_studio --url http://localhost:1234

# Text Generation WebUI
python3 review_classifier_advanced.py reviews.txt -p text_gen_webui --url http://localhost:5000
```

### Форматы входных файлов

**Текстовый файл (.txt):**
```
Первый отзыв
Второй отзыв
Третий отзыв
```

**JSON файл (.json):**
```json
[
  "Первый отзыв",
  "Второй отзыв", 
  "Третий отзыв"
]
```

Или:
```json
[
  {"отзыв": "Первый отзыв", "id": 1},
  {"отзыв": "Второй отзыв", "id": 2}
]
```

### Формат выходного файла

```json
[
  {
    "отзыв": "Не могу оплатить заказ картой",
    "категория": "Проблемы в работе приложения",
    "подкатегория": "Проблемы с оплатой",
    "теги": ["оплата", "ошибка_оплаты", "карта"]
  }
]
```

## Примеры использования

### 1. Простая классификация

```bash
# Создаем файл с отзывами
echo "Приложение постоянно зависает при запуске" > test_reviews.txt
echo "Отличная доставка, всё быстро!" >> test_reviews.txt

# Классифицируем
python3 review_classifier_advanced.py test_reviews.txt
```

### 2. Программное использование

```python
from review_classifier_advanced import AdvancedReviewClassifier

# Инициализация
classifier = AdvancedReviewClassifier("ollama")

# Классификация одного отзыва
annotation = classifier.classify_review_with_retry("Приложение тормозит")

if annotation:
    print(f"Категория: {annotation.category}")
    print(f"Подкатегория: {annotation.subcategory}")
    print(f"Теги: {annotation.tags}")
```

### 3. Пакетная обработка

```python
# Обработка файла
results = classifier.classify_reviews_from_file("large_reviews.txt")

# Получение статистики
stats = classifier.get_classification_stats(results)
print(f"Обработано: {stats['total_reviews']} отзывов")
```

## Настройка качества

### Параметры модели

Для улучшения качества классификации можно настроить:

- **temperature**: 0.1 (низкая = более детерминированные ответы)
- **top_p**: 0.9 (контроль разнообразия ответов)
- **max_tokens**: 300 (максимальная длина ответа)

### Выбор модели

**Для скорости:**
- llama3.2:1b (1.3GB) - самая быстрая
- gemma2:2b (1.6GB) - хороший баланс

**Для качества:**
- llama3.2:3b (2.0GB) - рекомендуемая
- qwen2.5:3b (2.2GB) - хорошо работает с русским

**Для максимального качества:**
- llama3.1:8b (4.7GB) - если есть достаточно RAM
- qwen2.5:7b (4.4GB) - отличное качество для русского языка

## Устранение проблем

### Проблема: "Не найден ни один работающий провайдер"

**Решение:**
1. Проверьте, запущен ли сервис:
   ```bash
   curl http://localhost:11434/api/tags  # Ollama
   curl http://localhost:1234/v1/models  # LM Studio
   ```

2. Установите провайдер:
   ```bash
   ./setup_ollama.sh
   ```

### Проблема: Низкое качество классификации

**Решение:**
1. Используйте более мощную модель
2. Проверьте, что reviews.json доступен для обучения
3. Увеличьте количество попыток (max_retries)

### Проблема: Медленная работа

**Решение:**
1. Используйте более легкую модель (llama3.2:1b)
2. Уменьшите max_tokens до 150-200
3. Используйте GPU ускорение (для Text Generation WebUI)

### Проблема: Ошибки JSON парсинга

**Решение:**
1. Система автоматически пытается исправить ошибки
2. Используйте temperature=0.1 для более стабильных ответов
3. Проверьте, что модель поддерживает русский язык

## Мониторинг и логи

Система выводит подробные логи:
- Процесс классификации каждого отзыва
- Ошибки и повторные попытки
- Статистику по завершении

Для отключения подробных логов можно перенаправить вывод:
```bash
python3 review_classifier_advanced.py reviews.txt > results.log 2>&1
```

## Интеграция в существующие системы

### API режим

Можно легко создать REST API:

```python
from flask import Flask, request, jsonify
from review_classifier_advanced import AdvancedReviewClassifier

app = Flask(__name__)
classifier = AdvancedReviewClassifier()

@app.route('/classify', methods=['POST'])
def classify_review():
    data = request.json
    review_text = data.get('review', '')
    
    annotation = classifier.classify_review_with_retry(review_text)
    
    if annotation:
        return jsonify({
            'category': annotation.category,
            'subcategory': annotation.subcategory,
            'tags': annotation.tags
        })
    else:
        return jsonify({'error': 'Classification failed'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

### Планировщик задач

Для автоматической обработки новых отзывов:

```bash
# Crontab для ежечасной обработки
0 * * * * /usr/bin/python3 /path/to/review_classifier_advanced.py /path/to/new_reviews.txt
```

## Производительность

**Примерная скорость обработки:**

| Модель | Скорость (отзывов/мин) | Качество |
|--------|------------------------|----------|
| llama3.2:1b | 20-30 | Хорошее |
| llama3.2:3b | 10-15 | Отличное |
| qwen2.5:3b | 8-12 | Отличное |
| llama3.1:8b | 3-5 | Превосходное |

*Результаты зависят от железа и сложности отзывов*

## Заключение

Система предоставляет гибкое и мощное решение для автоматической разметки отзывов с использованием локальных LLM. Начните с Ollama для простоты, затем экспериментируйте с другими провайдерами для оптимизации под ваши нужды.