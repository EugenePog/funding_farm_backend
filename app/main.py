from app import configuration
from app import logger
import json
from app.service.drift_funding_collector import drift_collector

async def collect_drift_funding_job():
    results = await drift_collector.get_all_funding_rates()

    return results

if __name__ == "__main__":
    try:
        with open(configuration.SETTINGS_FILE_PATH) as settings_file:
            # Load the settings file 
            settings = json.load(settings_file)

            api_num = int(settings['api_num'])

            for i in range(api_num):
                print(f"api: {i}")

            results = collect_drift_funding_job()

            print(f"{results}")

    except FileNotFoundError:
        logger.error(f"Settings file not found: {configuration.SETTINGS_FILE_PATH}")

    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON in settings file: {e}")

    except KeyError as e:
        logger.error(f"Missing required key in settings file: {e}")

    except ValueError as e:
        logger.error(f"Invalid value type (expected integer): {e}")

    except KeyboardInterrupt:
        logger.info(f"{configuration.PROJECT_NAME} interrupted by user.")

    except Exception as e:
        logger.exception(f"Unexpected error occurred: {e}")