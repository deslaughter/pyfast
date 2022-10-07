import openfast_library


def serial(input_file: str, library_path: str):
    openfastlib = openfast_library.FastLibAPI(library_path, input_file)
    openfastlib.fast_run()


if __name__ == "__main__":
    import sys
    import shutil
    if len(sys.argv) == 2:
        input_file = sys.argv[1]
        for ext in ['.so', '.dll', '.dylib']:
            library_path = shutil.which('libopenfastlib'+ext)
            if library_path:
                break
        else:
            raise Exception('unable to locate libopenfastlib.* in PATH')
        print("Using", library_path)
        serial(input_file, library_path)
    elif len(sys.argv) == 3:
        input_file, library_path = sys.argv[1:3]
        serial(input_file, library_path)
    else:
        print("usage: OpenFAST.py <input_file> [<library_path>]")
