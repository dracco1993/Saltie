import os

from conversions import binary_converter


def get_all_files():
    dir_path = os.path.dirname(os.path.realpath(__file__))
    training_path = dir_path + '\\training'
    files = []
    for (dirpath, dirnames, filenames) in os.walk(training_path):
        for file in filenames:
            files.append(dirpath + '\\' + file)
    return files

def get_input_function():
    #fill your input function here!
    import saltie
    bot = saltie.Agent('saltie', 0, 0)
    return binary_converter.default_process_pair

if __name__ == '__main__':
    files = get_all_files()
    print('training on files')
    print(files)
    input_function = get_input_function()
    for file in files:
        with open(file, 'r+b') as f:
            print('running file ' + file)
            binary_converter.read_data(f, input_function)
