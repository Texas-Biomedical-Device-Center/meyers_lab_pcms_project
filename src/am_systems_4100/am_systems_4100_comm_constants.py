class CONSTANTS:
    
    class MENU:

        GENERAL: int = 0
        CONFIG: int = 1
        IP_ADDR: int = 3
        UNIFORM_EVENT: int = 4
        TRAIN: int = 7
        EVENT_LIST: int = 8
        EVENT: int = 10

    class GENERAL:

        MODE: int = 0
        MONITOR: int = 1
        TRIGGER: int = 2
        AUTO: int = 3
        SAVE: int = 4
        ISO_OUTPUT: int = 5

    class CONFIG:

        PERIOD_OR_FREQ: int = 0
        SYNC_1: int = 1
        SYNC_2: int = 2
        SERIAL_NUMBER: int = 6

    class UNIFORM_EVENT:

        NUMBER: int = 0
    
    class TRAIN:

        TYPE: int = 0
        DELAY: int = 1
        DURATION: int = 2
        PERIOD: int = 3
        QUANTITY: int = 4
        OFFSET_OR_HOLD: int = 5
        LEVEL: int = 6

    class EVENT:

        TYPE: int = 2
        DELAY: int = 3
        QUANTITY: int = 4
        PERIOD: int = 5
        DUR_1: int = 6
        DUR_2: int = 8
        DUR_3: int = 9
        AMP_1: int = 7
        AMP_2: int = 10

class VALUES:

    class MENU_PAGE:

        GENERAL: int = 0
        CONFIG: int = 1
        IP_ADDR: int = 3
        TRAIN: int = 7
        EVENT_LIST: int = 8
        EVENT: int = 10 

    class MODE:

        INT_VOLT: int = 0
        INT_CURRENT: int = 1
        EXT_20V_PER_V: int = 2
        EXT_10MA_PER_V: int = 3
        EXT_1MA_PER_V: int = 4
        EXT_100UA_PER_V: int = 5

    class MONITOR:

        SCALE_100MV_PER_V: int = 0
        SCALE_1V_PER_V: int = 1
        SCALE_10V_PER_V: int = 2
        SCALE_20V_PER_V: int = 3
        SCALE_10UA_PER_V: int = 4
        SCALE_100UA_PER_V: int = 5
        SCALE_1MA_PER_V: int = 6
        SCALE_10MA_PER_V: int = 7
    
    class TRIGGER:

        RISING: int = 0
        FALLING: int = 1
    
    class AUTO:

        NONE: int = 0
        COUNT: int = 1
        FILL: int = 2
    
    class ISO_OUTPUT:

        ON: int = 0
        OFF: int = 1
    
    class PERIOD_OR_FREQ:

        PERIOD: int = 0
        FREQUENCY: int = 1
    
    class SYNC:

        TRAIN_DELAY: int = 0
        TRAIN_DURATION: int = 1
        EVENT_DELAY: int = 2
        EVENT_DURATION_1: int = 3
        EVENT_DURATION_2: int = 4
        EVENT_DURATION_3: int = 5
        EVENT_TOTAL_DURATION: int = 6
        CLOCK_US: int = 7
        CLOCK_MS: int = 8
    
    class TRAIN:

        class TYPE:

            UNIFORM: int = 0
            MIXED: int = 1
    
    class OFFSET_OR_HOLD:

        HOLD: int = 0
        OFFSET: int = 1

    class EVENT:

        class TYPE:

            MONOPHASIC: int = 0
            BIPHASIC: int = 1
            ASYMETRIC: int = 2
            RAMP: int = 3
