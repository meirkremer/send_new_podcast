import logging
import os
from datetime import datetime


class CustomFilter(logging.Filter):
    def __init__(self, modules_list):
        super().__init__()
        self._modules_list = modules_list

    def filter(self, record):
        return record.module in self._modules_list


loger = logging.getLogger(__name__)

loger.setLevel(logging.DEBUG)

log_number = str(len([log for log in os.listdir('log') if log.endswith('log')]) + 1)
handler = logging.FileHandler(f'log/{log_number}-{datetime.now().strftime("%H_%M_%S-%d_%m_%Y")}.log', encoding='utf-8')

formatter = logging.Formatter('%(levelname)s\n%(asctime)s\nmessage: %(message)s\n%(pathname)s line %(lineno)d\n')

handler.setFormatter(formatter)

my_modules = [module.split('.')[0] for module in os.listdir(os.getcwd()) if module.endswith('py')]
custom_filter = CustomFilter(my_modules)

handler.addFilter(custom_filter)

loger.addHandler(handler)
