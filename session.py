import string
import random

try:
    import json
except ImportError:
    from django.utils import simplejson as json

from google.appengine.ext import db

class SessionData(db.Model):

    data = db.TextProperty()
    date = db.DateTimeProperty(auto_now_add=True)

class Session(object):

    KEY_LENGTH = 64
    KEY_CHARS = string.letters + string.digits

    def __init__(self, key=None):

        if key is None:
            key = self.generate_key()

        self._key = key

        self._modified = False
        self._saved = False
        self._loaded = False

        self._entity = None
        self._data = {}

        self.load()

    def _get_modified(self):
        return self._modified

    def _set_modified(self, value):
        self._modified = value
        if value:
            self._saved = False
    modified = property(_get_modified, _set_modified)

    def _get_saved(self):
        return self._saved

    def _set_saved(self, value):
        self._saved = value
    saved = property(_get_saved, _set_saved)

    def get_key(self):
        return self._key

    def _get_entity(self):
        if self._entity:
            return self._entity

        key_name = self.get_key()
        self._entity = SessionData.get_by_key_name(key_name) or \
                            SessionData(key_name=key_name)
        return self._entity
    entity = property(_get_entity)

    def get_data(self):
        return self._data

    def get_json_data(self):
        return json.dumps(self.get_data())

    def generate_key(self):
        """ Generate a random key
        """
        return ''.join(random.choice(self.KEY_CHARS) for i in xrange(self.KEY_LENGTH))

    def key_exists(self, key):
        """ True if a session with this key exists, False otherwise
        """
        return SessionData.get_by_key_name(key) is not None

    def cycle_key(self):
        while True:
            key = self.generate_key()
            if not self.key_exists(key):
                break

        new_entity = SessionData(key_name=key, data=self.get_json_data())

        old_entity = self.entity
        if old_entity.is_saved():
            new_entity.date = old_entity.date
            old_entity.delete()

        new_entity.put()

        memcache.delete(self.get_key())
        self._key = key
        self._entity = new_entity
        
    def load(self):

        if self.is_loaded():
            return

        # Try loading from memcache first
        data = memcache.get(self.get_key())
        if data is not None:
            data = json.loads(data)
            if self.modified:
                data.update(self._data)
                self._data = data
            else:
                self._data.update(data)

        # Fall back to loading from the datastore
        else:
            entity = self.get_entity()
            if entity.is_saved():
                data = json.loads(entity.data)
                if self.modified:
                    data.update(self._data)
                    self._data = data
                else:
                    self._data.update(data)

        self._loaded = True

    def save(self):

        if self.saved:
            return

        data = json.dumps(self._data)

        # Save to memcache
        memcache.set(self.get_key(), data)

        # Save to datastore
        entity = self.get_entity()
        entity.data = data
        entity.put()

        self.saved = True
