""" debug druckt ggf.
            first: param1, param2
    aus
"""


def debug(c_o, first, *params):
    params_seperator = ""
    if c_o.flag_verbose:
        output = str(first)
        if params:
            output += ": "
            for p in params:
                output += params_seperator + str(p)
                params_seperator = ", "

        print(output)
