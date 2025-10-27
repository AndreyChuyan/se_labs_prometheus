# se_labs_prometheus

# Клонировать репозиторий
git clone https://github.com/AndreyChuyan/se_labs_prometheus.git

# Запустить все сервисы
cd monitoring-stack
make up

# Сгенерировать нагрузку
make load-test

# Включить chaos
make chaos-latency
make chaos-errors