import mongoengine
from marvinbot.utils import localized_date


class TrackedPackage(mongoengine.Document):
    id = mongoengine.SequenceField(primary_key=True)
    tracking_number = mongoengine.StringField(unique=True)

    subscribers = mongoengine.ListField(mongoengine.LongField())
    """Subscribers of this package."""

    updates = mongoengine.StringField(null=True)
    """Most recent updates from package."""

    date_page_fetched = mongoengine.DateTimeField(null=True)
    """Stores the last time this TrackedPackage was fetched for changes successfully."""

    date_updated = mongoengine.DateTimeField(null=True)
    """Stores the last time the package was updated."""

    num_errors = mongoengine.LongField(null=True)

    date_added = mongoengine.DateTimeField(default=localized_date)
    date_modified = mongoengine.DateTimeField(default=localized_date)
    date_deleted = mongoengine.DateTimeField(required=False, null=True)

    @classmethod
    def by_tracking_number(cls, tracking_number):
        try:
            return cls.objects.get(tracking_number=tracking_number)
        except cls.DoesNotExist:
            return None

    @classmethod
    def all(cls):
        try:
            return cls.objects(date_deleted=None)
        except:
            return None

    def __str__(self):
        return "{{ id = {id}, tracking_number = \"{tracking_number}\", updates = {updates}, subscribers = \"{subscribers}\", date_page_fetched = {date_page_fetched}, date_updated = {date_updated} }}".format(id=self.id, tracking_number=self.tracking_number, updates=self.updates, subscribers=", ".join(self.subscribers), date_page_fetched=self.date_page_fetched, date_updated=self.date_updated)
