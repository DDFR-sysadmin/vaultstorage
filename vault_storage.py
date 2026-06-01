#!/usr/bin/env python3
import os
import sys
import json
import getpass
import stat
import re
import argparse

# Главная директория хранилища
BASE_VAULT_DIR = "/opt/vaultstorage"

# ANSI-цвета для красивого вывода
COLOR_CYAN = "\033[96m"
COLOR_RESET = "\033[0m"

def _get_user_vault_path():
    """Определяет текущего пользователя и безопасно подготавливает его директорию."""
    current_user = os.environ.get("USER") or os.environ.get("LOGNAME")
    if not current_user:
        current_user = getpass.getuser()

    if not current_user or not re.match(r"^[a-zA-Z0-9_-]+$", current_user):
        print("[-] Ошибка: Не удалось безопасно определить текущего пользователя ОС.", file=sys.stderr)
        sys.exit(1)

    user_dir = os.path.join(BASE_VAULT_DIR, current_user)

    if not os.path.exists(user_dir):
        try:
            os.makedirs(user_dir, exist_ok=True)
            os.chmod(user_dir, 0o700)
        except PermissionError:
            print(f"[!] Ошибка: Нет прав на создание директории {user_dir}. Проверьте права на {BASE_VAULT_DIR}", file=sys.stderr)
            sys.exit(1)

    return user_dir

def _check_valid_secret_name(secret_name):
    """Проверяет вводимое название secret'а во избежание path traversal."""
    if not re.match(r"^[a-zA-Z0-9_-]+$", secret_name):
        print("[-] Ошибка: Недопустимое имя секрета!", file=sys.stderr)
        return True # Возвращаем True, если есть ошибка
    return False

def export_secrets(secret_name, data_dict):
    """Сохраняет словарь в персональный, защищённый JSON-файл."""
    if _check_valid_secret_name(secret_name):
        return False
    user_dir = _get_user_vault_path()
    file_path = os.path.join(user_dir, f"{secret_name}.json")

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data_dict, f, ensure_ascii=False, indent=4)
        os.chmod(file_path, 0o600)
        print(f"[+] Секрет '{secret_name}' успешно защищен и сохранен.")
        return True
    except Exception as e:
        print(f"[-] Ошибка записи секрета: {e}", file=sys.stderr)
        return False

def append_secrets(secret_name, data_dict):
    """Дописывает словарь в уже существующий JSON-файл."""
    if _check_valid_secret_name(secret_name):
        return False
    user_dir = _get_user_vault_path()
    file_path = os.path.join(user_dir, f"{secret_name}.json")

    if not os.path.exists(file_path):
        print(f"[-] Файл {file_path} отсутствует.", file=sys.stderr)
        return False

    file_stat = os.stat(file_path)
    permissions = stat.S_IMODE(file_stat.st_mode)
    if permissions != 0o600:
        print(f"[!] ВНИМАНИЕ: Файл {file_path} имеет небезопасные права: {oct(permissions)}. Модификация заблокирована!", file=sys.stderr)
        return False

    existing_data = import_secrets(secret_name)
    if existing_data is None:
        return False

    # Обновляем существующий словарь новыми данными (безопасно для старых версий Python)
    existing_data.update(data_dict)
    return export_secrets(secret_name, existing_data)

def import_secrets(secret_name):
    """Извлекает данные из персонального JSON-файла."""
    if _check_valid_secret_name(secret_name):
        return None
    user_dir = _get_user_vault_path()
    file_path = os.path.join(user_dir, f"{secret_name}.json")

    if not os.path.exists(file_path):
        print(f"[-] Секрет '{secret_name}' не найден.", file=sys.stderr)
        return None

    file_stat = os.stat(file_path)
    permissions = stat.S_IMODE(file_stat.st_mode)
    if permissions != 0o600:
        print(f"[!] ВНИМАНИЕ: Файл {file_path} имеет небезопасные права: {oct(permissions)}. Чтение заблокировано!", file=sys.stderr)
        return None

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"[-] Ошибка структуры файла: {file_path} не является валидным JSON.", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[-] Ошибка импорта секрета: {e}", file=sys.stderr)
        return None

def print_storage_contents(secret_name):
    """Выводит содержимое одного стораджа в красивом формате."""
    secrets = import_secrets(secret_name)
    if secrets is not None:
        print("_______________________________________")
        print(f"{COLOR_CYAN}{secret_name}{COLOR_RESET}")
        for k, v in secrets.items():
            print(f"{k}:{v}")

# --- CLI ИНТЕРФЕЙС ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="VaultStorage CLI — инструмент безопасного управления секретами.",
        formatter_class=argparse.RawTextHelpFormatter
    )

    # Имя секрета теперь опционально (чтобы работали флаги -sS и -sF без него)
    parser.add_argument("secret_name", nargs="?", help="Имя файла секрета (например, 'APIs')")

    # Основные флаги
    parser.add_argument("-i", dest="import_keys", nargs="+", help="Получить значения по ключам (через пробел или запятую)\nПример: vaultstorage google -i API, token")
    parser.add_argument("-a", dest="append_file", help="Дописать/обновить данные из указанного JSON-файла")
    parser.add_argument("-A", dest="append_kv", help="Добавить/обновить одну пару (формат 'ключ:значение')")
    parser.add_argument("-e", dest="export_file", help="Полностью перезаписать данные из указанного JSON-файла")
    parser.add_argument("-E", dest="export_kv", help="Полностью перезаписать данные одной парой (формат 'ключ:значение')")
    
    # Новые флаги для отображения
    parser.add_argument("-sS", "--show-secrets", dest="show_secrets", nargs="?", const="ALL", help="Показать содержимое стораджа (укажите имя или оставьте пустым для всех)")
    parser.add_argument("-sF", "--show-files", dest="show_files", action="store_true", help="Показать все доступные стораджи юзера")

    args = parser.parse_args()

    user_dir = _get_user_vault_path()

    # 1. Показать все файлы (-sF)
    if args.show_files:
        files = [f for f in os.listdir(user_dir) if f.endswith('.json')]
        if not files:
            print("[-] У вас пока нет сохраненных стораджей.")
        else:
            for f in files:
                print(f.replace('.json', ''))
        sys.exit(0)

    # 2. Показать содержимое секретов (-sS)
    if args.show_secrets:
        target = args.show_secrets
        # Обработка ситуации: vaultstorage google -sS
        if target == "ALL" and args.secret_name:
            target = args.secret_name

        if target == "ALL":
            files = [f for f in os.listdir(user_dir) if f.endswith('.json')]
            if not files:
                print("[-] У вас пока нет сохраненных стораджей.")
            else:
                for f in files:
                    print_storage_contents(f.replace('.json', ''))
        else:
            print_storage_contents(target)
        sys.exit(0)

    # Если мы дошли сюда, то для всех остальных операций нужно имя секрета
    if not args.secret_name:
        parser.print_help()
        sys.exit(1)

    # 3. Импорт конкретных ключей (-i)
    if args.import_keys:
        secrets = import_secrets(args.secret_name)
        if secrets is None:
            sys.exit(1)

        # Парсим ключи (обрабатываем как запятые, так и пробелы)
        raw_keys = " ".join(args.import_keys)
        keys_to_fetch = [k.strip() for k in raw_keys.replace(',', ' ').split() if k.strip()]

        if len(keys_to_fetch) == 1:
            key = keys_to_fetch[0]
            if key in secrets:
                print(secrets[key])
            else:
                print(f"[-] Ключ '{key}' не найден.", file=sys.stderr)
        else:
            for key in keys_to_fetch:
                if key in secrets:
                    print(f"{key}: {secrets[key]}")
                else:
                    print(f"[-] Ключ '{key}' не найден.", file=sys.stderr)
        sys.exit(0)

    # 4. Модификация данных (-e, -E, -a, -A)
    if args.export_file:
        try:
            with open(args.export_file, "r", encoding="utf-8") as f:
                new_data = json.load(f)
            export_secrets(args.secret_name, new_data)
            sys.exit(0)
        except Exception as e:
            print(f"[-] Ошибка импорта из файла {args.export_file}: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.export_kv:
        if ":" in args.export_kv:
            k, v = args.export_kv.split(":", 1)
            export_secrets(args.secret_name, {k.strip(): v.strip()})
            sys.exit(0)
        else:
            print("[-] Ошибка: Формат флага -E должен быть 'ключ:значение'", file=sys.stderr)
            sys.exit(1)

    elif args.append_file:
        try:
            with open(args.append_file, "r", encoding="utf-8") as f:
                new_data = json.load(f)
            success = append_secrets(args.secret_name, new_data)
            sys.exit(0 if success else 1)
        except Exception as e:
            print(f"[-] Ошибка дозаписи из файла {args.append_file}: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.append_kv:
        if ":" in args.append_kv:
            k, v = args.append_kv.split(":", 1)
            success = append_secrets(args.secret_name, {k.strip(): v.strip()})
            sys.exit(0 if success else 1)
        else:
            print("[-] Ошибка: Формат флага -A должен быть 'ключ:значение'", file=sys.stderr)
            sys.exit(1)

    # 5. Если передано только имя секрета, выводим весь JSON
    else:
        secrets = import_secrets(args.secret_name)
        if secrets:
            print(json.dumps(secrets, ensure_ascii=False, indent=4))
            sys.exit(0)
        sys.exit(1)
