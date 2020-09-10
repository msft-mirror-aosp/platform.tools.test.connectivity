import mimetypes
import os

from acts.test_utils.instrumentation.power.data_graph.utils import CSV_Monsoon_Reader
from acts.test_utils.instrumentation.power.data_graph.utils import ACTS_Monsoon_Reader
from acts.test_utils.instrumentation.power.data_graph.utils import CSV_PCM_Reader


def generate_chart(input_file, output_file, template_file):
  """Generate power chart by using monsoon data.

       Args:
           input_file: monsoon data file path.
           output_file: power chart html file path.
           template_file: template file path.
  """
  input_file_path = os.path.realpath(input_file)
  output_file_path = os.path.realpath(output_file)
  template_file_path = os.path.realpath(template_file)

  data = read_data(input_file_path)
  data_string = data.to_data_string()
  global_stats = data.get_statistics()

  with open(template_file_path, 'r') as template, open(output_file_path,
                                                       'w') as output:
    output.truncate()

    for line in template:
      if '[$POWERDATA]' in line:
        line = line.replace('[$POWERDATA]', data_string)
      elif '[$GLOBALMETRICS]' in line:
        line = line.replace(
            '[$GLOBALMETRICS]',
            str({
                k: (round(v, 3) if isinstance(v, float) else v)
                for k, v in global_stats.items()
            }))
      output.write(line)


def read_data(input_file):
  """Read monsoon data file."""
  file_type, _ = mimetypes.guess_type(input_file)

  if file_type is not None and file_type.startswith('text'):
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
  """Get monsoon data delimiter"""
  with open(file, 'r') as input_stream:
    line = input_stream.readline()
    if ',' in line:
      delimiter = ','
    elif ' ' in line:
      delimiter = ' '
    else:
      raise ValueError('Wrong data format!')
  return delimiter
