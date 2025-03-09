from insightface.app import FaceAnalysis

class FaceAppSingleton:
    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = FaceAnalysis(name="buffalo_l", providers=['CPUExecutionProvider'])
            cls._instance.prepare(ctx_id=0)  # Load the model only once
        return cls._instance

# Usage: Call `FaceAppSingleton.get_instance()` wherever needed.
