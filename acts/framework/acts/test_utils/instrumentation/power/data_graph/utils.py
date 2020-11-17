import csv

class CSV_Reader_Base(object):
  """Base class that implements common functionality for
  reading csv file.
  """

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
  """Class for reading acts monsoon file"""

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
  """Class for reading vzw dou manual assistant tool monsoon file"""

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
  """Class for monsoon data sampling"""

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
