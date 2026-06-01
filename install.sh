#!/bin/bash

# --- НАСТРОЙКИ ---
SOURCE_FILE="vault_storage.py"
TARGET_NAME="vaultstorage"
TARGET_DIR="/usr/bin"
VAULT_DIR="/opt/vaultstorage"

echo "=== Установка VaultStorage в систему ==="

# 1. Проверка прав: скрипт должен запускаться от root (через sudo)
# $EUID хранит ID пользователя, у root он всегда равен 0
if [ "$EUID" -ne 0 ]; then
    echo "[-] Ошибка: Для установки требуются права суперпользователя!" >&2
    echo "Пожалуйста, запустите скрипт через: sudo ./install.sh" >&2
    exit 1
fi

# 2. Проверка наличия исходного файла
if [ ! -f "$SOURCE_FILE" ]; then
    echo "[-] Ошибка: Файл $SOURCE_FILE не найден в текущей директории!" >&2
    exit 1
fi

# 3. Создание корневой директории для хранения секретов (/opt/vaultstorage)
echo "[+] Подготовка директории хранения: $VAULT_DIR"
mkdir -p "$VAULT_DIR"

# Выставляем права 1777 на корневую папку (Sticky Bit)
# Это значит, что любой пользователь системы может создавать там свои папки,
# но никто не может удалить чужую папку (так же работает системная /tmp)
chmod 1777 "$VAULT_DIR"

# 4. Копирование модуля в /usr/bin и переименование
echo "[+] Копирование утилиты в $TARGET_DIR/$TARGET_NAME"
cp "$SOURCE_FILE" "$TARGET_DIR/$TARGET_NAME"

# 5. Делаем файл исполняемым
echo "[+] Выставление прав на исполнение (chmod +x)"
chmod +x "$TARGET_DIR/$TARGET_NAME"

echo "----------------------------------------"
echo "[+] Установка успешно завершена!"
echo "Теперь вы можете использовать команду: vaultstorage --help"
