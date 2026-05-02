from src.config.settings import settings


def main() -> None:
    print("hello world")
    print("service: data-pipeline")
    print(f"environment: {settings.python_env}")


if __name__ == "__main__":
    main()
