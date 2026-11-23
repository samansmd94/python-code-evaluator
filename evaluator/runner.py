def run_function(function, arguments):
    try:
        result = function(*arguments)

        return {
            "result": result,
            "error": None
        }

    except Exception as error:
        return {
            "result": None,
            "error": str(error)
        }