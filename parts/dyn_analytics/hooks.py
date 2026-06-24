from datetime import datetime, timedelta
from random import randint


def post_init_hook(env):
    """
    Introduce some randomness to the moment the job is executed. Between 00:30:00 and 02:30:00 UTC.

    This spreads the load on the analytic endpoint.
    """
    cron = env.ref("dyn_analytics.cron_publish_analytics")
    cron.nextcall = datetime.now().replace(hour=0, minute=30, second=0) + timedelta(
        seconds=randint(0, 7200)
    )
