# Graphtec GP-GL Hardware-Native Bezier Splines and Carriage Observations

This document details the reverse-engineered mathematical syntax and physical verification of hardware-native cubic Bezier curves (`BZ1`) and provides exact physical clarifications on key coordinate and movement commands in the Graphtec GP-GL protocol.

---

## 1. Hardware-Native Bezier Splines (The `BZ1` Command)

### Background
Traditionally, vector cutting and plotting drivers render smooth curves by approximating them as thousands of tiny linear segments using a series of Draw (`D` or `E`) commands. While functional, this approach:
1.  Significantly increases the size of the transmitted USB payload.
2.  Can overwhelm the microcontroller's serial communication buffer, leading to mechanical "stuttering" or halting during complex, high-resolution curves.

Modern Graphtec firmware natively supports cubic Bezier interpolation at the hardware level through the `BZ` command structure (specifically `BZ1`). By offloading the curve rendering directly to the hardware interpolator, the plotter performs extremely fluid, uninterrupted physical cutting with negligible data overhead.

### Command Syntax and Parameter Mapping
The verified syntax for a native hardware-rendered cubic Bezier curve is:

```gpgl
BZ1,P0y,P0x,P1y,P1x,P2y,P2x,P3y,P3x,0\x03
```

Where:
*   **`BZ1`**: The command identifier for a Cubic Bezier Spline.
*   **`P0y, P0x`**: Coordinates of the start point ($P_0$).
*   **`P1y, P1x`**: Coordinates of the first control point ($P_1$).
*   **`P2y, P2x`**: Coordinates of the second control point ($P_2$).
*   **`P3y, P3x`**: Coordinates of the end point ($P_3$).
*   **`0`**: Termination parameter (always literal `0`, followed by the `\x03` command terminator).

The coordinates use standard GP-GL scaling units (matching the coordinates used in Draw `D` and Move `M` commands). 

### Python Generation Example
To generate a smooth native Bezier cut command programmatically:

```python
def generate_gpgl_bezier(p0, p1, p2, p3):
    """
    Generates a native GP-GL BZ1 cubic Bezier curve string.
    Parameters are tuples or lists of (x, y) coordinates.
    """
    # Map coordinates to the GP-GL BZ1 syntax format: BZ1,P0y,P0x,P1y,P1x,P2y,P2x,P3y,P3x,0
    gpgl_cmd = (
        f"BZ1,"
        f"{p0[1]:.2f},{p0[0]:.2f},"
        f"{p1[1]:.2f},{p1[0]:.2f},"
        f"{p2[1]:.2f},{p2[0]:.2f},"
        f"{p3[1]:.2f},{p3[0]:.2f},"
        f"0\x03"
    )
    return gpgl_cmd

# Example Usage:
# Define a smooth 90-degree curve in plotter coordinate units
start_point = (100.0, 100.0)
ctrl_point_1 = (100.0, 300.0)
ctrl_point_2 = (300.0, 300.0)
end_point = (300.0, 100.0)

bezier_command = generate_gpgl_bezier(start_point, ctrl_point_1, ctrl_point_2, end_point)
print(repr(bezier_command))
# Output: 'BZ1,100.00,100.00,300.00,100.00,300.00,300.00,100.00,300.00,0\x03'
```

---

## 2. Carriage Axis and Homing Physical Clarifications

Physical hardware verification has debunked several historical assumptions regarding coordinate setup and carriage feeding:

### Carriage Movement vs. Media Feed (`FO` and `FN` commands)
*   **Observed Behavior**: In modern firmware implementations (e.g., Graphtec/Silhouette Cameo 5 and Pro MK-II), the `FO[n]` and `FN[n]` commands control the **horizontal movement of the tool carriage (X-axis)**. 
*   **Clarification**: These commands do **not** feed or tracciona the media (Y-axis). Developers designing media-advancing routines should avoid using `FO` or `FN` for that purpose, as they will cause tool-head carriage displacement and potential mechanical collision.

### Logic Scaling Boundary (`Z` command)
*   **Observed Behavior**: The `Z[x],[y]` command is Graphtec's `Write Upper Right` function. 
*   **Clarification**: `Z` performs a virtual, software-level scaling recalculation of the logical plotting area. It is **not** a physical command for feeding, home-positioning, or ejecting paper. Misuse of the `Z` command at the end of a transmission can cause scale distortion in subsequent cutting jobs.

### Mechanical Tool Initialization Bypass
*   **Observed Behavior**: By sending explicit calibration queries and setting physical tool characteristics via manual command structures (`FA` / manual blade profiles), the plotter completely bypasses the noisy mechanical AutoBlade depth-adjustment tapping sequence.
*   **Clarification**: This allows immediate transition from registration mark sensing to active vector cutting, saving significant time and reducing structural wear on the tool head carriage.
