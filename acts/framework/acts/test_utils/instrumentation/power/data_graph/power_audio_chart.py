import argparse
import csv
import mimetypes
import os

def __main():
  parser = argparse.ArgumentParser()
  parser.add_argument("--input-file", dest="input_file", required=True,
                      help="Input file: csv or raw pcm (binary) to generate data. Required")
  parser.add_argument("--output-file", dest="output_file", required=True,
                      help="Output file: something.html for the output graph. Required")
  parser.add_argument("--template-file", dest="template_file", required=True,
                    help="format html file absolute path. Required")

  args = parser.parse_args()

  input_file_path = os.path.realpath(args.input_file)
  output_file_path = os.path.realpath(args.output_file)
  template_file_path = os.path.realpath(args.template_file)

  data = read_data(input_file_path)
  write_data(template_file_path, output_file_path, data)


def read_data(input_file):
  file_type, _ = mimetypes.guess_type(input_file)

  if file_type is not None and file_type.startswith("text"):
    delimiter = guess_csv_delimiter(input_file)
    if delimiter == ',':
      data = CSV_Monsoon_Reader()
      data.extract_data_from_file(input_file)
    else:
      data = ACTS_Monsoon_Reader()
      data.extract_data_from_file(input_file)
  else:
    data = CSV_PCM_Reader()
    data.extract_data_from_file(input_file)

  return data

def guess_csv_delimiter(file):
  with open(file, 'r') as input_stream:
    line = input_stream.readline()
    if ',' in line:
      delimiter = ','
    elif ' ' in line:
      delimiter = ' '
    else:
      raise ValueError('Wrong data format!')
  return delimiter

def write_data(template_file, output_file, data):
  data_string = data.to_data_string()
  global_stats = data.get_statistics()

  with open(template_file, "r") as template, open(output_file, "w") as output:
    output.truncate()

    for line in template:
      if "[$POWERDATA]" in line:
        line = line.replace("[$POWERDATA]", data_string)
      elif "[$GLOBALMETRICS]" in line:
        line = line.replace("[$GLOBALMETRICS]", \
        str({k: (round(v, 3) if isinstance(v, float) else v) for k, v in global_stats.items()}))
      output.write(line)


class CSV_Reader_Base(object):
  def __init__(self):
    self.data = []

  def extract_data_from_file(self, input_file):
    raise NotImplementedError

  def to_data_string(self):
    data_string = '['
    for entry in self.data:
      data_string += f'[{entry[0]},{entry[1]:.2f},0,0],\n'
    data_string += ']'
    return data_string

  def get_statistics(self):
    current_data = [entry[1] for entry in self.data]
    return {
        'average': sum(current_data) / len(current_data),
        'maxValue': max(current_data),
        'minValue': min(current_data),
        'duration': self.data[-1][0] - self.data[0][0]
    }


class ACTS_Monsoon_Reader(CSV_Reader_Base):

  def extract_data_from_file(self, input_file):
    with open(input_file, 'r') as csv_file:
      csv_monsoon = csv.DictReader(csv_file, delimiter=' ', fieldnames=['Time (s)', 'Current (A)'])
      self.read_acts_monsoon_csv(csv_monsoon)

  def read_acts_monsoon_csv(self, csv_monsoon):
    self.data = []
    begin_timestamp = None
    row_no = 0
    reduce_to_10_percent = True

    for data_entry in csv_monsoon:
      if data_entry['Time (s)'] is None or \
          data_entry['Current (A)'] is None:
        print(f'Missing data entry at {row_no + 1}! Please check your data input.')
      else:
        timestamp = int(float(data_entry['Time (s)']) * 1000)
        current = float(data_entry['Current (A)']) * 1000

        if row_no == 1:
          time_delta = timestamp - begin_timestamp
          if time_delta < 2:
            reduce_to_10_percent = True
          else:
            reduce_to_10_percent = False

        if row_no % 10 == 0 or not reduce_to_10_percent:
          if current < 0:
            current = 0

          if begin_timestamp is None:
            begin_timestamp = timestamp

          timestamp = timestamp - begin_timestamp
          self.data.append([timestamp, current])

        row_no += 1

class CSV_Monsoon_Reader(CSV_Reader_Base):
  def __init__(self):
    super().__init__()
    self._INDICATOR_VALUE = 3000

  def extract_data_from_file(self, input_file):
    with open(input_file, 'r') as csv_file:
      csv_monsoon = csv.DictReader(csv_file)
      self.read_monsoon_csv(csv_monsoon)

  def read_monsoon_csv(self, csv_monsoon):
    self.data = []
    begin_timestamp = None
    row_no = 0
    reduce_to_10_percent = True

    for data_entry in csv_monsoon:
      if data_entry['Time (s)'] is None or \
          data_entry['Main Avg Current (mA)'] is None:
        # We need to count the header, that's why it's + 2 and not + 1
        print(f'Missing data entry at {row_no + 2}! Please check your data input.')
      else:
        timestamp = float(data_entry['Time (s)']) * 1000
        current = float(data_entry['Main Avg Current (mA)'])

        if row_no == 1:
          time_delta = timestamp - begin_timestamp
          if time_delta < 2:
            reduce_to_10_percent = True
          else:
            reduce_to_10_percent = False

        if row_no % 10 == 0 or not reduce_to_10_percent:
          if current < 0:
            current = 0
          elif current > self._INDICATOR_VALUE:
            current = 2500

          if begin_timestamp is None:
            begin_timestamp = timestamp

          timestamp = timestamp - begin_timestamp
          self.data.append([timestamp, current])

        row_no += 1

  def get_statistics(self):
    current_data = [entry[1] for entry in self.data if entry[1] < self._INDICATOR_VALUE]
    return {
        'average': sum(current_data) / len(current_data),
        'maxValue': max(current_data),
        'minValue': min(current_data),
        'duration': self.data[-1][0] - self.data[0][0]
    }

class CSV_PCM_Reader(CSV_Reader_Base):
  def __init__(self):
    super().__init__()
    self._PCM_FREQUENCY = 44100

  def extract_data_from_file(self, input_file):
    self.data = []
    microsecond_per_frame = 1 / self._PCM_FREQUENCY * 1000

    with open(input_file, 'rb') as pcm_input:
      raw_data = pcm_input.read(1)
      timestamp = 0
      while raw_data:
        amplitude = ord(raw_data)
        self.data.append([timestamp, amplitude])
        timestamp += microsecond_per_frame
        raw_data = pcm_input.read(1)

if __name__ == "__main__":
  __main()
