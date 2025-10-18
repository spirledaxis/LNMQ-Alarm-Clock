class Schedule:
    "Schedules some callback function everyday at a certain hour and minute"

    def __init__(self):
        self.jobs = []  # list of (hour, minute, callback, triggered)
        raise NotImplementedError("Not tested whatsoever!")

    def add_job(self, hour, minute, callback):
        """Add a scheduled job. Hour should be 24 hour time"""
        self.jobs.append({
            "hour": hour,
            "minute": minute,
            "callback": callback,
            "triggered": False
        })

    def reset(self):
        """Reset all jobs to allow triggering again (e.g., next day)."""
        for job in self.jobs:
            job["triggered"] = False

    def update(self):
        """Check current time and run jobs if needed."""
        now = rtc.datetime()
        hour = now[4]
        minute = now[5]

        for job in self.jobs:
            if (job["hour"] == hour and job["minute"]
                    == minute and not job["triggered"]):
                job["callback"]()
                job["triggered"] = True

            # reset the triggered flag
            elif job["minute"] != minute and job["triggered"]:
                job["triggered"] = False
