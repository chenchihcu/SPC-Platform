from enum import Enum

class SampleMode(str, Enum):
    FIRST = "首件"
    ALL = "全件"
    SAMPLE = "抽樣"
