#!/usr/bin/env python3
"""
Конфигурации для различных локальных LLM API
Поддерживает: Ollama, LM Studio, Text Generation WebUI, LocalAI и другие
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
import requests
import json


class LLMProvider(ABC):
    """Абстрактный базовый класс для провайдеров LLM"""
    
    @abstractmethod
    def query(self, prompt: str, **kwargs) -> Optional[str]:
        """Отправляет запрос к LLM и возвращает ответ"""
        pass


class OllamaProvider(LLMProvider):
    """Провайдер для Ollama API"""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.2:3b"):
        self.base_url = base_url
        self.model = model
    
    def query(self, prompt: str, **kwargs) -> Optional[str]:
        try:
            url = f"{self.base_url}/api/generate"
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": kwargs.get("temperature", 0.1),
                    "top_p": kwargs.get("top_p", 0.9),
                    "num_predict": kwargs.get("max_tokens", 200)
                }
            }
            
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            return result.get('response', '').strip()
            
        except Exception as e:
            print(f"Ошибка Ollama API: {e}")
            return None


class LMStudioProvider(LLMProvider):
    """Провайдер для LM Studio API"""
    
    def __init__(self, base_url: str = "http://localhost:1234", model: str = "local-model"):
        self.base_url = base_url
        self.model = model
    
    def query(self, prompt: str, **kwargs) -> Optional[str]:
        try:
            url = f"{self.base_url}/v1/chat/completions"
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": kwargs.get("temperature", 0.1),
                "max_tokens": kwargs.get("max_tokens", 200),
                "stream": False
            }
            
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            return result['choices'][0]['message']['content'].strip()
            
        except Exception as e:
            print(f"Ошибка LM Studio API: {e}")
            return None


class TextGenWebUIProvider(LLMProvider):
    """Провайдер для Text Generation WebUI API"""
    
    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
    
    def query(self, prompt: str, **kwargs) -> Optional[str]:
        try:
            url = f"{self.base_url}/api/v1/generate"
            payload = {
                "prompt": prompt,
                "max_new_tokens": kwargs.get("max_tokens", 200),
                "temperature": kwargs.get("temperature", 0.1),
                "top_p": kwargs.get("top_p", 0.9),
                "do_sample": True,
                "seed": -1,
                "add_bos_token": True,
                "truncation_length": 2048,
                "ban_eos_token": False,
                "skip_special_tokens": True,
                "stopping_strings": []
            }
            
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            return result['results'][0]['text'].strip()
            
        except Exception as e:
            print(f"Ошибка Text Generation WebUI API: {e}")
            return None


class LocalAIProvider(LLMProvider):
    """Провайдер для LocalAI API"""
    
    def __init__(self, base_url: str = "http://localhost:8080", model: str = "gpt-3.5-turbo"):
        self.base_url = base_url
        self.model = model
    
    def query(self, prompt: str, **kwargs) -> Optional[str]:
        try:
            url = f"{self.base_url}/v1/chat/completions"
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": kwargs.get("temperature", 0.1),
                "max_tokens": kwargs.get("max_tokens", 200)
            }
            
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            return result['choices'][0]['message']['content'].strip()
            
        except Exception as e:
            print(f"Ошибка LocalAI API: {e}")
            return None


class LlamaFileProvider(LLMProvider):
    """Провайдер для llamafile (автономный исполняемый файл)"""
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
    
    def query(self, prompt: str, **kwargs) -> Optional[str]:
        try:
            url = f"{self.base_url}/completion"
            payload = {
                "prompt": prompt,
                "n_predict": kwargs.get("max_tokens", 200),
                "temperature": kwargs.get("temperature", 0.1),
                "top_p": kwargs.get("top_p", 0.9),
                "stream": False
            }
            
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            return result.get('content', '').strip()
            
        except Exception as e:
            print(f"Ошибка llamafile API: {e}")
            return None


# Конфигурации для разных провайдеров
LLM_CONFIGS = {
    "ollama": {
        "provider": OllamaProvider,
        "default_params": {
            "base_url": "http://localhost:11434",
            "model": "llama3.2:3b"
        },
        "description": "Ollama - простой в установке, хорошо работает с русским языком"
    },
    
    "lm_studio": {
        "provider": LMStudioProvider,
        "default_params": {
            "base_url": "http://localhost:1234",
            "model": "local-model"
        },
        "description": "LM Studio - удобный GUI для загрузки и запуска моделей"
    },
    
    "text_gen_webui": {
        "provider": TextGenWebUIProvider,
        "default_params": {
            "base_url": "http://localhost:5000"
        },
        "description": "Text Generation WebUI - много настроек, поддержка GPU"
    },
    
    "localai": {
        "provider": LocalAIProvider,
        "default_params": {
            "base_url": "http://localhost:8080",
            "model": "gpt-3.5-turbo"
        },
        "description": "LocalAI - совместимый с OpenAI API"
    },
    
    "llamafile": {
        "provider": LlamaFileProvider,
        "default_params": {
            "base_url": "http://localhost:8080"
        },
        "description": "llamafile - один исполняемый файл, очень простая установка"
    }
}


def create_llm_provider(provider_name: str = "ollama", **kwargs) -> Optional[LLMProvider]:
    """Создает экземпляр провайдера LLM"""
    
    if provider_name not in LLM_CONFIGS:
        print(f"Неизвестный провайдер: {provider_name}")
        print(f"Доступные провайдеры: {list(LLM_CONFIGS.keys())}")
        return None
    
    config = LLM_CONFIGS[provider_name]
    provider_class = config["provider"]
    
    # Объединяем параметры по умолчанию с переданными
    params = {**config["default_params"], **kwargs}
    
    try:
        return provider_class(**params)
    except Exception as e:
        print(f"Ошибка создания провайдера {provider_name}: {e}")
        return None


def test_provider(provider: LLMProvider) -> bool:
    """Тестирует работу провайдера"""
    test_prompt = "Привет! Ответь одним словом: да"
    
    try:
        response = provider.query(test_prompt)
        if response and len(response.strip()) > 0:
            print(f"✓ Провайдер работает. Ответ: {response[:50]}...")
            return True
        else:
            print("✗ Провайдер не вернул ответ")
            return False
    except Exception as e:
        print(f"✗ Ошибка тестирования провайдера: {e}")
        return False


def find_working_provider() -> Optional[LLMProvider]:
    """Ищет первый работающий провайдер из списка"""
    
    print("Поиск работающего провайдера LLM...")
    
    for provider_name, config in LLM_CONFIGS.items():
        print(f"\nТестируем {provider_name}: {config['description']}")
        
        provider = create_llm_provider(provider_name)
        if provider and test_provider(provider):
            print(f"✓ Найден работающий провайдер: {provider_name}")
            return provider
        else:
            print(f"✗ Провайдер {provider_name} недоступен")
    
    print("\n✗ Не найден ни один работающий провайдер")
    return None


if __name__ == "__main__":
    # Демонстрация работы
    print("=== Тестирование провайдеров LLM ===")
    
    # Показываем доступные провайдеры
    print("\nДоступные провайдеры:")
    for name, config in LLM_CONFIGS.items():
        print(f"- {name}: {config['description']}")
    
    # Ищем работающий провайдер
    working_provider = find_working_provider()
    
    if working_provider:
        print(f"\n=== Тест классификации отзыва ===")
        test_review = "Приложение постоянно зависает, очень неудобно"
        
        prompt = f"""Классифицируй отзыв: "{test_review}"
        
Ответь в формате JSON:
{{
    "категория": "название",
    "подкатегория": "название",
    "теги": ["тег1", "тег2"]
}}"""
        
        response = working_provider.query(prompt)
        print(f"Ответ LLM: {response}")
    else:
        print("\nДля работы системы необходимо установить один из провайдеров LLM")
        print("Рекомендуется начать с Ollama: bash setup_ollama.sh")