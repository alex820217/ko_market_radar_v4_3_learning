from dataclasses import dataclass
import math
@dataclass(frozen=True)
class Profile:
    investment:float=1500;stop_pct:float=5;max_stop_pct:float=8;target_pct:float=10;trail_step:float=5;leverage_min:float=4;leverage_max:float=6;ko_min:float=17;ko_max:float=23;max_spread:float=1.5
def trailing_stop(entry,performance,p):
    if performance<p.trail_step:return entry*(1-p.stop_pct/100)
    locked=math.floor(performance/p.trail_step)*p.trail_step-p.trail_step
    return entry*(1+locked/100)
