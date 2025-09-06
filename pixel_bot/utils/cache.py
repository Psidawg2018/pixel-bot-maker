class ImageCache:
    def __init__(self):
        self._cache = {}

    def get(self, key):
        return self._cache.get(key)

    def put(self, key, value):
        self._cache[key] = value

    def clear(self):
        self._cache.clear()

# Global instance to be used across the application
image_cache = ImageCache()
