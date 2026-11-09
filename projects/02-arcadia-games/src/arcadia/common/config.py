from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parents[3]
VERSION = "1.0.0"

@dataclass(frozen=True)
class Config:
    profile: str
    players: int
    seed: int
    start: datetime
    end: datetime
    ranges: dict

    def __post_init__(self):
        if self.players < 1 or self.seed < 0 or self.start.tzinfo is None or self.end.tzinfo is None or self.end <= self.start:
            raise ValueError("Invalid player count, seed or aware observation window")


def load_config(profile="development"):
    values = tomllib.loads((ROOT / "config/profiles.toml").read_text())[profile]
    return Config(profile, values["players"], values["seed"], datetime.fromisoformat(values["start"]),
                  datetime.fromisoformat(values["end"]), {k: v for k, v in values.items() if k.endswith("_range")})
