
from utils.progress_utils import Progress


class BaseModelResult():

    def __init__(self):
        return

    def get_image_path(self):
        return None

    def get_video_path(self):
        return None

    def get_audio_path(self):
        return None

class BaseModel():

    def __init__(self):
        return

    async def text2image(self,prompt:str,save_dir:str, progress:Progress):
        return

    async def image2video(self,input_image_path:str, prompt:str,save_dir:str, progress:Progress):
        return
