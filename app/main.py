from app import settings
from app import logger
import json

if __name__ == "__main__":
    try:
        with open(settings.CONFIG_FILE_PATH) as config_file:
            # Load the configuration file 
            config = json.load(config_file)

            api_num = int(config['api_num'])
    except KeyboardInterrupt:
        logger.info('{config.PROJECT_NAME} interrupted by user.')