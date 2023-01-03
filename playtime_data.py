from datetime import datetime as dt
from datetime import timedelta
from collections import OrderedDict
import os
import gzip
import matplotlib.pyplot as plt
import matplotlib
import numpy as np

matplotlib.use('TkAgg')

log_dir = r'D:/proto backup/logs/'
crash_dir = r'D:proto backup/crash-reports/'

data = {}
auth_wait = {}


def open_file(file):
    if '.gz' in file:
        with gzip.open(file, 'rb') as f:
            ff = f.readlines()
    else:
        with open(file, 'r') as f:
            ff = f.readlines()
    return ff


def get_ts(file: str, line_time: str):
    """returns timestamp from log line"""
    time = dt.strptime(file[:10] + line_time, "%Y-%m-%d%H:%M:%S")
    return dt.timestamp(time)


def process_file(fdir, file):  # TODO implement crash report to give ends to playtimes
    try:
        ff = open_file(fdir + file)
        for line in ff:
            if '.gz' in file:
                line = line.decode('utf-8')
            line_time, line_type, line_content = line.split("]", 2)
            line_time = line_time[1:]
            line_type = line_type[2:]
            line_content = line_content[2:].replace('\n', '')

            if 'User Authenticator' in line_type:
                name = line_content[15:].rsplit(' ', 2)[0]
                uuid = line_content.rsplit(' ', 1)[1]
                auth_wait[name] = uuid

            elif line_type == 'Server thread/INFO':
                name = line_content.split(' joined the game')[0].split(' left the game')[0]
                if name in auth_wait and name[0] != '<' and name[-1] != '>' and 'joined the game' in line_content:
                    uuid = auth_wait[name]
                    if uuid not in data:
                        data[uuid] = []
                    ts = get_ts(file, line_time)
                    data[uuid].append({'name': name, 'start': ts})

                if name in auth_wait and name[0] != '<' and name[-1] != '>' and 'left the game' in line_content:
                    uuid = auth_wait[name]
                    ts = get_ts(file, line_time)
                    data[uuid][-1]['end'] = ts

    except Exception as e:
        pass


def graph():
    fig, ax = plt.subplots(figsize=(100, 20))

    time_start = min([session['start'] for player in data for session in data[player]])
    time_end = max([session['end'] for player in data for session in data[player] if 'end' in session])
    start = dt.fromtimestamp(time_start)
    end = dt.fromtimestamp(time_end)
    months = OrderedDict(((start + timedelta(_)).strftime(r"%b-%y"), None) for _ in range((end - start).days)).keys()
    timestamps = [dt.timestamp(dt.strptime(month, "%b-%y")) for month in months]
    ax.set_xticks(timestamps)
    ax.set_xticklabels(months)
    name_bottom = data[[k for k in data.keys()][0]][-1]['name']
    name_top = data[[k for k in data.keys()][-1]][-1]['name']

    for player in data:
        try:
            name = data[player][-1]['name']
            plt.plot([time_start, time_end], [name, name], '', color='gray', alpha=0.25, linewidth=1)

        except Exception as e:
            pass

        for session in data[player]:
            try:
                start = session['start']
                end = session['end']
                plt.plot([start, end], [name, name], '', linewidth=4)

            except Exception as e:
                pass

    for timestamp in timestamps:
        ax.plot([timestamp, timestamp], [name_bottom, name_top], '', color='black', alpha=0.5, linewidth=1)

    plt.savefig("Proto.pdf")
    plt.show()


def format_time(timestamp):
    hours = timestamp // 3600
    timestamp -= (hours * 3600)
    minutes = timestamp // 60
    seconds = timestamp - (minutes * 60)
    return '{:02}:{:02}:{:02}'.format(int(hours), int(minutes), int(seconds))


def player_time(name):
    uuid = None
    for player in data:
        for session in data[player]:
            if session["name"] == name:
                uuid = player
                break

    if uuid:
        playtimes = []
        for session in data[uuid]:
            try:
                tdelta = session["end"] - session["start"]
                playtimes.append(tdelta)
            except Exception as e:
                print(session, e)

        print(f"Logged in {len(data[uuid])} times")
        print(f"Total playtime: {format_time(sum(playtimes))}")
        print(f"Average playtime: {format_time(np.average(playtimes))}")
        print(f"Median playtime: {format_time(np.median(playtimes))}")
        print(f"Last played: {dt.strftime(dt.fromtimestamp(data[uuid][-1]['start']), '%Y-%m-%d %X')} for {format_time(playtimes[-1])}")

    else:
        print(f"No player found with name {name}")


def fix_data():
    for player in data:
        to_remove = []
        for i in range(len(data[player])):
            if 'end' not in data[player][i]:
                to_remove.append(i)
        for j in reversed(to_remove):
            data[player].pop(j)


def crash_fix(fdir, file):
    ff = open_file(fdir + file)
    file_time = dt.strptime(file.replace('crash-', '').replace('-server.txt', ''), '%Y-%m-%d_%H.%M.%S').timestamp()
    for line in ff:
        if 'Player Count' in str(line):
            for player in data:
                for session in data[player]:
                    if 'end' not in session and session['name'] in line:
                        pos = data[player].index(session)
                        if session['start'] < file_time < data[player][pos + 1]['start'] and len(data[player]) > pos:
                            data[player][pos]['end'] = file_time


def main():
    log_files = [f for f in os.listdir(log_dir)]
    for file in log_files:
        process_file(log_dir, file)

    crash_files = [f for f in os.listdir(crash_dir)]
    for file in crash_files:
        crash_fix(crash_dir, file)

    fix_data()
    # graph()
    player_time("DoomSkull")


if __name__ == '__main__':
    main()
