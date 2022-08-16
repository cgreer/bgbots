from dataclasses import dataclass


@dataclass
class Settings:
    display_best_actions: bool = True
    display_puct_info: bool = False
    display_consideration_stats: bool = True
    display_environment_state: bool = True

    def disable_output(self):
        self.display_best_actions = False
        self.display_puct_info = False
        self.display_consideration_stats = False
        self.display_environment_state = False


SETTINGS = Settings()
