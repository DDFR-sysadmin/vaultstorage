#!/bin/bash

# --- НАСТРОЙКИ ---
TARGET_NAME="vaultstorage"
TARGET_DIR="/usr/bin"
VAULT_DIR="/opt/vaultstorage"

echo "=== Удаление VaultStorage из системы ==="

# Проверка прав (root)
if [ "$EUID" -ne 0 ]; then
    echo "[-] Ошибка: Для удаления требуются права суперпользователя!" >&2
    echo "Пожалуйста, запустите скрипт через: sudo ./uninstall.sh" >&2
    exit 1
fi

# 1. Удаление самого исполняемого файла
if [ -f "$TARGET_DIR/$TARGET_NAME" ]; then
    rm -f "$TARGET_DIR/$TARGET_NAME"
    echo "[+] Утилита $TARGET_NAME успешно удалена из $TARGET_DIR."
else
    echo "[-] Исполняемый файл $TARGET_NAME не найден в $TARGET_DIR."
fi

# 2. Интерактивное удаление базы с секретами
if [ -d "$VAULT_DIR" ]; then
    echo -n "[?] Вы хотите удалить все сохраненные секреты пользователей из $VAULT_DIR? [y/N]: "
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        rm -rf "$VAULT_DIR"
        echo "[+] Директория с секретами $VAULT_DIR была удалена."
    else
        echo "[*] Директория $VAULT_DIR сохранена."
    fi
else
    echo "[*] Директория с секретами $VAULT_DIR не найдена."
fi

echo "----------------------------------------"
echo "[+] Деинсталляция успешно завершена!"
