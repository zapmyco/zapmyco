"""
语音服务模块。

此模块提供了语音输入和语音转文本的功能，
支持实时麦克风监听和语音识别。
"""

import asyncio
import logging
import os
import queue
import threading
import time
from typing import Callable, Optional, Dict, Any

import pyaudio
import numpy as np
import dashscope
from dashscope.audio.asr import TranslationRecognizerChat, TranscriptionResult, TranslationResult

from zapmyco.config import settings

logger = logging.getLogger(__name__)


class VoiceError(Exception):
    """语音服务错误基类。"""
    pass


class RecognitionError(VoiceError):
    """语音识别错误。"""
    pass


class MicrophoneError(VoiceError):
    """麦克风错误。"""
    pass


class VoiceCallback:
    """语音识别回调类。"""
    
    def __init__(self, text_callback: Callable[[str], None]):
        """
        初始化语音识别回调。
        
        Args:
            text_callback: 文本回调函数，当识别到文本时调用
        """
        self.text_callback = text_callback
        self.transcription_text = ""
        self.is_final = False
    
    def on_open(self) -> None:
        """连接打开时的回调。"""
        logger.debug("语音识别会话已打开")
    
    def on_close(self) -> None:
        """连接关闭时的回调。"""
        logger.debug("语音识别会话已关闭")
    
    def on_event(
        self,
        request_id,
        transcription_result: TranscriptionResult,
        translation_result: TranslationResult,
        usage,
    ) -> None:
        """
        事件回调。
        
        Args:
            request_id: 请求ID
            transcription_result: 转录结果
            translation_result: 翻译结果
            usage: 使用情况
        """
        if transcription_result is not None:
            self.transcription_text = transcription_result.text
            logger.debug(f"识别文本: {self.transcription_text}")
            
            # 如果是最终结果，调用回调函数
            if transcription_result.is_end:
                self.is_final = True
                if self.text_callback and self.transcription_text:
                    self.text_callback(self.transcription_text)
    
    def on_error(self, message) -> None:
        """
        错误回调。
        
        Args:
            message: 错误消息
        """
        logger.error(f"语音识别错误: {message}")
        raise RecognitionError(f"语音识别错误: {message}")
    
    def on_complete(self) -> None:
        """完成回调。"""
        logger.debug("语音识别完成")


class VoiceService:
    """
    语音服务类。
    
    提供麦克风录音和语音转文本功能。
    """
    
    def __init__(self, text_callback: Optional[Callable[[str], None]] = None):
        """
        初始化语音服务。
        
        Args:
            text_callback: 文本回调函数，当识别到文本时调用
        """
        # 配置
        self.api_key = settings.DASHSCOPE_API_KEY
        if not self.api_key:
            raise ValueError("DASHSCOPE_API_KEY 未设置，无法使用语音服务")
        
        # 设置 API Key
        dashscope.api_key = self.api_key
        
        # 音频参数
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000  # 采样率必须是16kHz
        self.chunk = 1024
        self.record_seconds = 5
        
        # 状态
        self.is_listening = False
        self.stop_listening = False
        self.text_callback = text_callback
        
        # 组件
        self.audio = None
        self.stream = None
        self.translator = None
        self.callback = None
        self.listen_thread = None
        
        # 音频队列
        self.audio_queue = queue.Queue()
        
        # 初始化 PyAudio
        self.audio = pyaudio.PyAudio()
    
    def __del__(self):
        """析构函数，确保资源被释放。"""
        self.stop()
        if self.audio:
            self.audio.terminate()
    
    def start(self, wake_word: Optional[str] = None) -> None:
        """
        开始监听麦克风。
        
        Args:
            wake_word: 唤醒词，如果设置，则只有在检测到唤醒词后才会开始处理
        """
        if self.is_listening:
            logger.warning("语音服务已经在监听中")
            return
        
        # 初始化回调
        self.callback = VoiceCallback(self.text_callback)
        
        # 初始化翻译器
        self.translator = TranslationRecognizerChat(
            model="gummy-chat-v1",
            format="pcm",  # 使用 PCM 格式，与 PyAudio 兼容
            sample_rate=self.rate,
            callback=self.callback,
        )
        
        # 启动翻译器
        self.translator.start()
        
        # 重置停止标志
        self.stop_listening = False
        self.is_listening = True
        
        # 启动监听线程
        self.listen_thread = threading.Thread(target=self._listen_microphone)
        self.listen_thread.daemon = True
        self.listen_thread.start()
        
        logger.info("语音服务已启动，正在监听麦克风")
    
    def stop(self) -> None:
        """停止监听麦克风。"""
        if not self.is_listening:
            return
        
        # 设置停止标志
        self.stop_listening = True
        
        # 等待线程结束
        if self.listen_thread and self.listen_thread.is_alive():
            self.listen_thread.join(timeout=2.0)
        
        # 停止流
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        
        # 停止翻译器
        if self.translator:
            self.translator.stop()
            self.translator = None
        
        self.is_listening = False
        logger.info("语音服务已停止")
    
    def _listen_microphone(self) -> None:
        """
        监听麦克风的内部方法。
        在单独的线程中运行。
        """
        try:
            # 打开麦克风流
            self.stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                frames_per_buffer=self.chunk,
            )
            
            logger.info("麦克风已打开，开始录音")
            
            # 持续录音直到停止
            while not self.stop_listening:
                try:
                    # 读取音频数据
                    audio_data = self.stream.read(self.chunk, exception_on_overflow=False)
                    
                    # 发送音频数据到翻译器
                    if not self.translator.send_audio_frame(audio_data):
                        # 如果发送失败，可能是句子结束
                        logger.debug("句子结束，重新开始监听")
                        # 重新启动翻译器
                        self.translator.stop()
                        self.translator.start()
                
                except Exception as e:
                    logger.error(f"录音过程中出错: {str(e)}")
                    # 短暂暂停后继续
                    time.sleep(0.1)
        
        except Exception as e:
            logger.error(f"麦克风监听线程出错: {str(e)}")
            self.is_listening = False
            raise MicrophoneError(f"麦克风监听失败: {str(e)}")
        
        finally:
            # 确保资源被释放
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
                self.stream = None
            
            if self.translator:
                self.translator.stop()
                self.translator = None
            
            self.is_listening = False


class AsyncVoiceService:
    """
    异步语音服务类。
    
    提供异步接口的麦克风录音和语音转文本功能。
    """
    
    def __init__(self):
        """初始化异步语音服务。"""
        self.voice_service = None
        self.text_queue = asyncio.Queue()
        self._running = False
    
    async def start(self, wake_word: Optional[str] = None) -> None:
        """
        异步启动语音服务。
        
        Args:
            wake_word: 唤醒词，如果设置，则只有在检测到唤醒词后才会开始处理
        """
        if self._running:
            return
        
        # 创建文本回调函数
        def text_callback(text: str) -> None:
            # 将识别到的文本放入队列
            asyncio.run_coroutine_threadsafe(
                self.text_queue.put(text), 
                asyncio.get_event_loop()
            )
        
        # 创建语音服务
        self.voice_service = VoiceService(text_callback=text_callback)
        
        # 启动语音服务
        self.voice_service.start(wake_word=wake_word)
        self._running = True
    
    async def stop(self) -> None:
        """异步停止语音服务。"""
        if not self._running:
            return
        
        if self.voice_service:
            self.voice_service.stop()
            self.voice_service = None
        
        self._running = False
    
    async def get_text(self) -> str:
        """
        获取识别到的文本。
        
        Returns:
            识别到的文本
        """
        if not self._running:
            raise RuntimeError("语音服务未启动")
        
        # 等待队列中的文本
        text = await self.text_queue.get()
        return text


if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(level=logging.DEBUG)
    
    # 测试同步版本
    def on_text(text):
        print(f"识别到文本: {text}")
    
    # 创建语音服务
    voice_service = VoiceService(text_callback=on_text)
    
    try:
        # 启动语音服务
        voice_service.start()
        
        # 等待10秒
        print("请对着麦克风说话，10秒后自动停止...")
        time.sleep(10)
    
    finally:
        # 停止语音服务
        voice_service.stop()
    
    # 测试异步版本
    async def test_async():
        # 创建异步语音服务
        async_voice = AsyncVoiceService()
        
        try:
            # 启动语音服务
            await async_voice.start()
            
            # 等待文本
            print("请对着麦克风说话，等待识别结果...")
            text = await asyncio.wait_for(async_voice.get_text(), timeout=10.0)
            print(f"异步识别到文本: {text}")
        
        finally:
            # 停止语音服务
            await async_voice.stop()
    
    # 运行异步测试
    asyncio.run(test_async())
