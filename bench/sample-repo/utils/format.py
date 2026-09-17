"""Number formatting shared by the report."""


def fixed(value, places=3):
    return ("%." + str(places) + "f") % value
