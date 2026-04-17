import time

caption_stages = [
"> start robotics",
"led blink\ndopamine ↑",
"stm32\nsanity ↓",
"timer config\n????????",
"assembly\nWHY ARE WE STILL HERE",
"PID\n\"this is fine\"\n*robot violently shakes*",
"odometry\n\"simple math\"\n*teleports*",
"localization\nI AM GOD",
"fuse:\nno.",
"robot:\n↗ instead of ↑",
"me:\nok",
"*works once*",
"me:\ndon't breathe near it",
"deadzone bug\nencoder noise\nbattery sag\nexistential dread",
"junior:\nyou live here now"
]

robot_stages = [
"""
  [^_^]
  /| |\\
   / \\
""",
"""
  [o_o]
  /| |\\
   / \\
""",
"""
  [-_-]
  /| |\\
   / \\
""",
"""
  [o_O]
  /| |\\
   / \\
""",
"""
  [>_<]
  /| |\\
   / \\
""",
"""
  [T_T]
  /| |\\
   / \\
""",
"""
  [@_@]
  /| |\\
   / \\
""",
"""
  [^O^]
  /| |\\
   / \\
""",
"""
  [x_x]
  /| |\\
   / \\
""",
"""
  [o_o]
  /| |\\
   / \\
""",
"""
  [^_^]
  /| |\\
   / \\
""",
"""
  [>_<]
  /| |\\
   / \\
""",
"""
  [T_T]
  /| |\\
   / \\
""",
"""
  [💀]
  /| |\\
   / \\
"""
]

print("Starting Robotics Simulation...\n")

time.sleep(1)

for i in range(len(caption_stages)):
    print(caption_stages[i])
    print(robot_stages[i % len(robot_stages)])
    print("\n")
    time.sleep(1)

print("Simulation ended.")