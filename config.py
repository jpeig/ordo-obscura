class Config:
    REDIS_URI = "redis://:password@localhost:6379/0"
    OOB_HOST_WS = 'localhost:5005'
    OOB_HOST_HTTP = 'localhost:5000'
    OOB_URI_WS = f'ws://{OOB_HOST_WS}/api/v1/stream'
    OOB_URI_HTTP = f'http://{OOB_HOST_HTTP}/api/v1/generate'
    DEBUG = True
    HOST = '127.0.0.1'
    PORT = 8001
    SKIP_GEN_MISSION = False
    SKIP_GEN_EVENT = False
    SKIP_GEN_STATE = False
    SKIP_VAL1 = """{}"""
    SKIP_VAL2 = """{}"""

