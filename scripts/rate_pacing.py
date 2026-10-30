"""Conservative rolling-minute pacing for accelerated offline model experiments."""
import math
import time


class PacingError(ValueError):
    pass


class MinutePacer:
    def __init__(self,clock=time.monotonic,sleep=time.sleep,rpm=45,tpm=300000):
        self.clock,self.sleep=clock,sleep
        self.rpm,self.tpm=rpm,tpm
        self.events=[]

    def reserve(self,completions,tokens,deadline):
        if not 0<completions<=self.rpm or not 0<tokens<=self.tpm:
            raise PacingError('one request group exceeds the experiment pacing capacity')
        waited=0.0
        while True:
            now=self.clock()
            if now>=deadline:
                raise PacingError('runtime exhausted before experiment dispatch')
            self.events=[event for event in self.events if event[0]>now-60]
            count=sum(event[1] for event in self.events)
            token_count=sum(event[2] for event in self.events)
            if count+completions<=self.rpm and token_count+tokens<=self.tpm:
                self.events.append((now,completions,tokens))
                return waited
            delay=min(event[0]+60-now for event in self.events)+.001
            if not math.isfinite(delay) or now+delay>deadline:
                raise PacingError('runtime would expire while waiting for experiment pacing; no dispatch')
            # Bounded waits remain interruptible and count in real experiment time.
            pause=min(30,delay)
            self.sleep(pause);waited+=pause
