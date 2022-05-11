import os
import time
import argparse
import signal
import cv2

DEBUG = False
PIXEL = '▀'

interrupted = False

def create_pixels(rgb_up, rgb_down):
    pixels = f'\x1b[38;2;{rgb_up[0]};{rgb_up[1]};{rgb_up[2]}m'
    if rgb_down is not None:
        pixels += f'\x1b[48;2;{rgb_down[0]};{rgb_down[1]};{rgb_down[2]}m'
    pixels += PIXEL

    return pixels

def print_image(image, move_cursor_back):
    term_size = os.get_terminal_size()

    term_height = (term_size.lines - 1) * 2
    term_width = term_size.columns

    if image.shape[0] >= term_width or image.shape[1] >= term_height:
        resize_factor = min(term_width / image.shape[1], term_height / image.shape[0])
        image = cv2.resize(
            image,
            dsize=(int(image.shape[1] * resize_factor), int(image.shape[0] * resize_factor)),
            interpolation = cv2.INTER_AREA
        )

    string_rows = []
    for i in range(0, image.shape[0], 2):
        string_row = ''
        for pixel_up, pixel_down in zip(image[i], image[i + 1] if image.shape[0] > i + 1 else iter(lambda: None, 0)):
            string_row += create_pixels(pixel_up, pixel_down)
        string_row += '\x1b[0m'
        string_rows.append(string_row)

    if move_cursor_back:
        print(f'\033[{(image.shape[0] + 1) // 2 - 1}A' + f'\033[{image.shape[1]}D', end='', flush=True)
    print('\n'.join(string_rows), end='', flush=True)

def print_animated(path, loop):
    try:
        path = int(path)
    except ValueError:
        if not os.path.isfile(path):
            print('error: given path is not an existing file or camera id')
            exit(1)

    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frame_duration = 1 / fps

    last_time = time.time()

    first_frame = True
    while not interrupted:
        ret, frame = cap.read()

        if not ret:
            if loop:
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
            else:
                break

        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        print_image(frame, move_cursor_back=not first_frame)
        first_frame = False
        if DEBUG: print(f'=== frame {cap.get(cv2.CAP_PROP_POS_FRAMES)}/{frame_count}')

        curr_time = time.time()
        last_time += frame_duration
        if last_time - curr_time >= 0:
            time.sleep(last_time - curr_time)
        else:
            if DEBUG: print('can\'t keep up with framerate')

    print()

def interrupt_handler(sig, frame):
    global interrupted
    interrupted = True

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='plays a gif, video or shows your camera in your terminal')
    parser.add_argument('source', type=str, help='file path or camera id')
    parser.add_argument('-l', '--loop', action='store_true', help='repeat the gif/video indefinitely')
    args = parser.parse_args()

    old_handler = signal.signal(signal.SIGINT, interrupt_handler)
    print_animated(args.source, loop=args.loop)
    signal.signal(signal.SIGINT, old_handler)
