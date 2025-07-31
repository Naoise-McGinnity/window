import ctypes

def get_windows_api_accent_color():
    color = ctypes.c_uint()
    opaque = ctypes.c_bool()

    dwmapi = ctypes.WinDLL("dwmapi")

    res = dwmapi.DwmGetColorizationColor(ctypes.byref(color), ctypes.byref(opaque))
    if res != 0:
        print(f"Failed to get color, error code: {res}")
        return None

    argb = color.value
    a = (argb >> 24) & 0xFF
    r = (argb >> 16) & 0xFF
    g = (argb >> 8) & 0xFF
    b = argb & 0xFF

    return (r, g, b, a)
