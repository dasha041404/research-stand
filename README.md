# Research Stand: Prometheus vs VictoriaMetrics

Сравнение связок Prometheus+Grafana и VictoriaMetrics+Grafana для мониторинга метрик социальной активности студентов волонтёрской платформы Университета ИТМО.

## Требования

- Windows 11 x64
- Docker Desktop с WSL 2 backend (запущен)
- Python 3.12
- PowerShell 7+

## Установка окружения

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install pyyaml pandas numpy scipy matplotlib
Запуск эксперимента
powershell
# Поднять стенд
docker compose up -d app db prometheus grafana cadvisor

# Запустить прогоны (параметры в configs/experiment.yaml)
python runner\run_experiment.py --config configs\experiment.yaml --backend both

# Анализ результатов
python analysis\analyze.py --input results\raw --output results\processed

# Остановить
docker compose down -v
Структура проекта
sut/ — FastAPI-приложение (имитация волонтёрской платформы)

load/ — Locust-сценарии поведенческой активности

monitoring/ — конфиг Prometheus

runner/ — оркестрация прогонов + манифесты

analysis/ — статистика (медиана, IQR, bootstrap CI, Mann–Whitney, Cliff's δ)

results/raw/ — сырые CSV и JSON-манифесты

results/processed/ — агрегированные таблицы и графики

Воспроизводимость
Каждый прогон сохраняет манифест: git-commit, версии образов, seed, параметры, характеристики машины. Проверяющий может сравнить свой манифест с эталонным.

text

### Шаг 2. Сохраните файл
Нажмите **Ctrl+S**.

### Шаг 3. Отправьте изменения на GitHub
Выполните в PowerShell по очереди:

```powershell
git add README.md
git commit -m "Add README instructions"
git push
