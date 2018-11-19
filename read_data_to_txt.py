from transCoordinateSystem import wgs84_to_bd09
import xlrd
import xlwt

file_path = 'C:\\Users\\hgvgh\\Desktop\\宜出行热力图抓取\\easygo\\example\\example2018-11-19-10-25-19.txt'

def read_result_to_points(file_path):

    '''
    将easygo的数据转换为百度地图热力图显示的格式
    :param file_path:
    :return:
    '''
    points = []
    with open(file_path) as f:
        lines = f.readlines()
        i = 0

        # 将数据写入EXCEL中
        book = xlwt.Workbook(encoding='utf-8', style_compression=0)
        sheet = book.add_sheet('0', cell_overwrite_ok=True)
        # 第一行(列标题)
        sheet.write(0, 0, 'lng')
        sheet.write(0, 1, 'lat')
        sheet.write(0, 2, 'count')

        for line in lines:
            i += 1
            if i == 1:
                continue
            line_str  = line.split(',')
            count = int(float(line_str[0]))
            lng = float(line_str[1])
            lat = float(line_str[2])
            lng, lat = wgs84_to_bd09(lng, lat)

            one_point = {}
            one_point['lng'] = lng
            one_point['lat'] = lat
            one_point['count'] = count
            points.append(one_point)

            sheet.write(i - 1, 0, lng)
            sheet.write(i - 1, 1, lat)
            sheet.write(i - 1, 2, count)

        book.save('data_flow.xls')


    with open('data_flow.txt', 'w') as f:
        f.write('[')
        i = 0
        print('总共有', len(points), '个热力点')
        for line in points:
            f.write(str(line) + ',')
        f.write(']')




read_result_to_points(file_path)
