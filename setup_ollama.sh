#!/bin/bash

# Скрипт для установки и настройки Ollama для разметки отзывов

echo "=== Установка Ollama ==="

# Проверяем, установлен ли уже Ollama
if command -v ollama &> /dev/null; then
    echo "Ollama уже установлен"
else
    echo "Устанавливаем Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
fi

echo "=== Запуск Ollama сервиса ==="
# Запускаем Ollama в фоне
ollama serve &
OLLAMA_PID=$!
echo "Ollama запущен с PID: $OLLAMA_PID"

# Ждем запуска сервиса
sleep 5

echo "=== Загрузка рекомендуемых моделей ==="

# Модели для разных задач (от легких к тяжелым)
declare -a models=(
    "llama3.2:1b"      # Очень легкая модель (1.3GB)
    "llama3.2:3b"      # Легкая модель (2.0GB) - рекомендуемая
    "qwen2.5:3b"       # Хорошая альтернатива (2.2GB)
    "gemma2:2b"        # Еще одна легкая модель (1.6GB)
)

echo "Доступные модели для установки:"
for i in "${!models[@]}"; do
    echo "$((i+1)). ${models[$i]}"
done

echo ""
echo "Рекомендуется установить llama3.2:3b (модель #2) для оптимального баланса качества и скорости"
echo ""

# Устанавливаем рекомендуемую модель
echo "Устанавливаем рекомендуемую модель llama3.2:3b..."
ollama pull llama3.2:3b

echo ""
echo "=== Проверка установки ==="
ollama list

echo ""
echo "=== Тест модели ==="
echo "Тестируем модель на простом примере..."
ollama run llama3.2:3b "Привет! Ответь кратко: ты готов помогать с анализом отзывов на русском языке?"

echo ""
echo "=== Установка завершена! ==="
echo ""
echo "Ollama запущен и готов к работе!"
echo "API доступен по адресу: http://localhost:11434"
echo ""
echo "Для использования системы разметки отзывов запустите:"
echo "python3 review_classifier.py"
echo ""
echo "Чтобы остановить Ollama, выполните: kill $OLLAMA_PID"

# Сохраняем PID для возможности остановки
echo $OLLAMA_PID > ollama.pid
echo "PID сохранен в файл ollama.pid"