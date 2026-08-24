# from .models import init_db

from .models import (
    init_db,
    upsert_beacon,
    get_beacon,
    get_all_beacons,
    mark_dead_beacons,
    create_task,
    get_pending_tasks,
    get_all_tasks,
    store_result,
    get_results,
    get_recent_results,
)