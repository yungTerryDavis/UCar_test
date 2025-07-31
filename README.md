# UCar test task

## Установка и запуск
```sh
pip install fastapi uvicorn
uvicorn app:app
```

## Тестирование
```sh
# Добавление отзыва
curl -X POST "http://localhost:8000/reviews" -H "Content-Type: application/json" -d '{"text": "томас шелби хорош"}'

# Вывод отзывов. sentiment=[positive, negative, neutral], опционально
curl "http://localhost:8000/reviews?sentiment=positive"
```