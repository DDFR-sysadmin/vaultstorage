import os
import sys
import json
import getpass
import stat
import re
# Главная директория хранилища
BASE_VAULT_DIR = "/opt/vaultstorage"


def _get_user_vault_path():
    """
    Внутренняя функция: определяет текущего пользователя и
    безопасно подготавливает его персональную директорию.
    """
    # 1. Узнаем, от чьего имени запущен скрипт
    current_user = getpass.getuser()

    # 2. Формируем путь: /opt/vaultstorage/имя пользователя запустившего скрипт с этой либой
    user_dir = os.path.join(BASE_VAULT_DIR, current_user)

    # 3. Безопасное создание директории
    if not os.path.exists(user_dir):
        try:
            # Создаем папку. exist_ok=True предотвращает ошибку, если папка появится в процессе
            os.makedirs(user_dir, exist_ok=True)

            # ВАЖНО: Принудительно ставим права 700 (drwx------).
            # Мы делаем это явно, так как дефолтный системный umask может попытаться дать права 755
            os.chmod(user_dir, 0o700)
        except PermissionError:
            print(f"[!] Ошибка: Нет прав на создание директории {user_dir}. Проверьте права на {BASE_VAULT_DIR}",
                  file=sys.stderr)
            sys.exit(1)

    return user_dir

def _check_valid_secret_name(secret_name):
    """
    Внутренняя функция: нужна во избежание ../../path traversal
    проверяет вводимое название secret'а
    """
    if not re.match(r"^[a-zA-Z0-9_-]+$", secret_name):
        print("[-] Ошибка: Недопустимое имя секрета!", file=sys.stderr)
        return 1


def export_secrets(secret_name, data_dict):
    """
    Сохраняет словарь в персональный, защищённый JSON-файл.
    :param secret_name: Имя секрета (например, 's3_keys' -> превратится в s3_keys.json)
    :param data_dict: Словарь с данными для сохранения
    """
    user_dir = _get_user_vault_path()
    if _check_valid_secret_name(secret_name):
        return None
    file_path = os.path.join(user_dir, f"{secret_name}.json")

    try:
        # Пишем данные в файл
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data_dict, f, ensure_ascii=False, indent=4)

        # Принудительно выставляем права 600 (-rw-------)
        os.chmod(file_path, 0o600)
        print(f"[+] Секрет '{secret_name}' успешно защищен и сохранен.")

    except Exception as e:
        print(f"[-] Ошибка записи секрета: {e}", file=sys.stderr)


def append_secrets(secret_name, data_dict):
    """
    Дописывает словарь уже существующий JSON-файл.
    :param secret_name: Имя секрета
    :param data_dict: Словарь с данными которые должны быть добавлены
    """
    user_dir = _get_user_vault_path()
    if _check_valid_secret_name(secret_name):
        return None
    file_path = os.path.join(user_dir, f"{secret_name}.json")


    # Проверяем достуупность файла и отсутствие его компроментации
    if not os.path.exists(file_path):
        print(f"Файл {file_path} отсутствует.")
        return None
    else:
        file_stat = os.stat(file_path)
        permissions = stat.S_IMODE(file_stat.st_mode)
        if permissions != 0o600:
            print(f"[!] ВНИМАНИЕ: Файл {file_path} имеет небезопасные права: {oct(permissions)}. Чтение заблокировано!",
                  file=sys.stderr)
            return None

    # Делаем объеденённый словарь из уже существующих данных и данных которые мы хотим записать
    # Если встречается ключ, который есть и в существующих и во вводимых данных, то значение у ключа будет установленно из новых данных
    data_dict = import_secrets(secret_name) | data_dict
    #Пишем данные уже существующей функцией
    export_secrets(secret_name, data_dict)




def import_secrets(secret_name):
    """
    Извлекает данные из персонального JSON-файла.
    :param secret_name: Имя секрета для чтения
    :return: Словарь с данными или None в случае ошибки
    """
    user_dir = _get_user_vault_path()
    if _check_valid_secret_name(secret_name):
        return None
    file_path = os.path.join(user_dir, f"{secret_name}.json")

    if not os.path.exists(file_path):
        print(f"[-] Секрет '{secret_name}' не найден.", file=sys.stderr)
        return None

    # --- БЛОК АУДИТА БЕЗОПАСНОСТИ ---
    # Проверяем, не скомпрометированы ли права на файл перед его чтением
    file_stat = os.stat(file_path)
    permissions = stat.S_IMODE(file_stat.st_mode)  # Получаем только биты прав

    # 0o600 в десятеричной системе - это 384. Если права шире, бьем тревогу.
    if permissions != 0o600:
        print(f"[!] ВНИМАНИЕ: Файл {file_path} имеет небезопасные права: {oct(permissions)}. Чтение заблокировано!",
              file=sys.stderr)
        return None
    # --------------------------------

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"[-] Ошибка структуры файла: {file_path} не является валидным JSON.", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[-] Ошибка импорта секрета: {e}", file=sys.stderr)
        return None






# Делаем комфортное консольное взаимодействие
if __name__ == "__main__":
    import argparse

    # Создаем парсер аргументов командной строки
    parser = argparse.ArgumentParser(
        description="VaultStorage CLI — инструмент безопасного управления секретами."
    )

    # Первым обязательным аргументом всегда идет имя хранилища (секрета)
    parser.add_argument("secret_name", help="Имя файла секрета (например, 'APIs')")

    # Второй аргумент — опциональный (ключ для чтения, если запускаем без флагов)
    parser.add_argument("key", nargs="?", help="Ключ, значение которого нужно прочитать")

    # Группа флагов для модификации данных (флаги не должны конфликтовать друг с другом)
    parser.add_argument("-a", dest="append_file", help="Дописать/обновить данные из указанного JSON-файла")
    parser.add_argument("-A", dest="append_kv", help="Добавить/обновить одну пару 'ключ:значение' напрямую")
    parser.add_argument("-e", dest="export_file", help="Полностью перезаписать данные из указанного JSON-файла")
    parser.add_argument("-E", dest="export_kv", help="Полностью перезаписать данные одной парой 'ключ:значение'")

    # Разбираем пришедшие аргументы
    args = parser.parse_args()

    # --- ЛОГИКА ОБРАБОТКИ ФЛАГОВ ---

    # 1. Флаг -e: Полная перезапись из файла
    if args.export_file:
        try:
            with open(args.export_file, "r", encoding="utf-8") as f:
                new_data = json.load(f)
            export_secrets(args.secret_name, new_data)
            sys.exit(0)
        except Exception as e:
            print(f"[-] Ошибка импорта из файла {args.export_file}: {e}", file=sys.stderr)
            sys.exit(1)

    # 2. Флаг -E: Полная перезапись одной парой Ключ:Значение
    elif args.export_kv:
        if ":" in args.export_kv:
            k, v = args.export_kv.split(":", 1)  # Сплитим только по первому двоеточию
            export_secrets(args.secret_name, {k.strip(): v.strip()})
            sys.exit(0)
        else:
            print("[-] Ошибка: Формат флага -E должен быть 'ключ:значение'", file=sys.stderr)
            sys.exit(1)

    # 3. Флаг -a: Дозапись/обновление из файла
    elif args.append_file:
        try:
            with open(args.append_file, "r", encoding="utf-8") as f:
                new_data = json.load(f)
            success = append_secrets(args.secret_name, new_data)
            sys.exit(0 if success else 1)
        except Exception as e:
            print(f"[-] Ошибка дозаписи из файла {args.append_file}: {e}", file=sys.stderr)
            sys.exit(1)

    # 4. Флаг -A: Дозапись/обновление одной пары Ключ:Значение
    elif args.append_kv:
        if ":" in args.append_kv:
            k, v = args.append_kv.split(":", 1)
            success = append_secrets(args.secret_name, {k.strip(): v.strip()})
            sys.exit(0 if success else 1)
        else:
            print("[-] Ошибка: Формат флага -A должен быть 'ключ:значение'", file=sys.stderr)
            sys.exit(1)

    # 5. Режим чтения (если никакие флаги модификации не переданы)
    else:
        if args.key:
            # Читаем секрет целиком
            secrets = import_secrets(args.secret_name)
            if secrets and args.key in secrets:
                # Выводим ТОЛЬКО значение ключа (для Bash)
                print(secrets[args.key])
                sys.exit(0)
            else:
                print(f"[-] Ключ '{args.key}' или секрет '{args.secret_name}' не найден.", file=sys.stderr)
                sys.exit(1)
        else:
            # Если передано только имя секрета без флагов и без конкретного ключа,
            # выведем весь JSON (полезно для быстрого просмотра глазами)
            secrets = import_secrets(args.secret_name)
            if secrets:
                print(json.dumps(secrets, ensure_ascii=False, indent=4))
                sys.exit(0)
            sys.exit(1)