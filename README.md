# Nexus 桌面效率助手

基于「上位机 (Python) + 下位机 (MCU)」架构的硬件级桌面自动化终端。

## 核心特性

- **纯物理 HID 输出**：硬件 USB HID 报文直发，操作系统无法区分软件注入与物理设备
- **多屏自适应**：动态注入虚拟桌面总分辨率，无缝支持异构多屏
- **仿生运动学引擎**：Fitts' Law + Woodworth 双组分模型，贝塞尔弧线 Delta-Time 物理缓动
- **行为长尾模拟**：对数正态分布 (Log-Normal) 驱动按压时长与操作间隔

---

## 快速开始

### 1. 烧录下位机固件

准备一块带原生 USB 的开发板（**Arduino Leonardo / Micro** 或 **RP2040**）。

在 Arduino IDE 中安装 [AbsMouse](https://github.com/jonathanedgecombe/AbsMouse) 库，复制以下代码并烧录：

```cpp
#include <AbsMouse.h>   // https://github.com/jonathanedgecombe/AbsMouse

int screenW = 1920;
int screenH = 1080;

void setup() {
  Serial.begin(115200);
  AbsMouse.init(screenW, screenH);
  // 注意: 不要调用 Mouse.begin()，否则会覆盖绝对坐标 HID 描述符
}

void loop() {
  if (Serial.available() > 0) {
    String data = Serial.readStringUntil('\n');
    data.trim();

    if (data == "NEXUS_REQ") {
      Serial.println("NEXUS_ACK");
    }
    else if (data.startsWith("R,")) {
      // 动态分辨率同步: R,<width>,<height>
      int c1 = data.indexOf(',');
      int c2 = data.indexOf(',', c1 + 1);
      if (c1 != -1 && c2 != -1) {
        screenW = data.substring(c1 + 1, c2).toInt();
        screenH = data.substring(c2 + 1).toInt();
        AbsMouse.init(screenW, screenH);
      }
    }
    else if (data.startsWith("M,")) {
      // 绝对坐标移动: M,<x>,<y>
      int c1 = data.indexOf(',');
      int c2 = data.indexOf(',', c1 + 1);
      if (c1 != -1 && c2 != -1) {
        int tx = data.substring(c1 + 1, c2).toInt();
        int ty = data.substring(c2 + 1).toInt();
        if (tx >= 0 && ty >= 0 && tx <= screenW && ty <= screenH) {
          AbsMouse.move(tx, ty);
        }
      }
    }
    else if (data == "D") { AbsMouse.press(); }
    else if (data == "U") { AbsMouse.release(); }
  }
}
```

### 2. 安装上位机依赖

```bash
pip install -r requirements.txt
```

### 3. 启动

```bash
python host_software/cl4.py
```

- 点击「添加区域」框选目标操作区域
- （可选）选择串口并点击「连接设备」激活硬件旁路模式
- 点击「启动」开始执行

### 4. 紧急停止

按键盘 **Q** 键，或将鼠标移至屏幕左上角 (0,0)（仅软件模式）

---

## 串口协议

| 方向 | 指令 | 含义 |
|------|------|------|
| PC → MCU | `NEXUS_REQ` | 握手请求 |
| MCU → PC | `NEXUS_ACK` | 握手确认 |
| PC → MCU | `R,<w>,<h>` | 同步虚拟桌面分辨率 |
| PC → MCU | `M,<x>,<y>` | 移动光标至绝对坐标 |
| PC → MCU | `D` | 鼠标按下 |
| PC → MCU | `U` | 鼠标释放 |

---

## 注意事项

- 下位机必须使用带原生 USB HID 能力的 MCU（ATmega32U4 / RP2040），普通 Arduino Uno 不可用
- 上位机握手成功后会自动发送当前桌面虚拟分辨率，无需手动配置
- 多屏用户的虚拟分辨率 ≠ 单屏物理分辨率，固件默认值仅作初始占位
