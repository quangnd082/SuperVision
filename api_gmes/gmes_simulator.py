from flask import Flask, request, jsonify
import random
import string
import json
from datetime import datetime

app = Flask(__name__)
# Hàm tạo chuỗi ngẫu nhiên
def random_string(length=8):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

# Các thông số mặc định
FACTORY_CODE = "C5H0A"
PLANT_CODE = "P514"

# Mẫu dữ liệu để tìm kiếm theo serial number
SAMPLE_DATA = {
    # Serial number: S51V237829-S51V237839
    # Thêm các dữ liệu mẫu từ gmes_api.json ở đây
}

# Đọc dữ liệu từ gmes_api.json (nếu có)
try:
    with open('gmes_api.json', 'r') as file:
        lines = file.readlines()
        
    current_serial = None
    model_info_dict = {}
    box_info_dict = {}
    inspection_dict = {}
    all_data_dict = {}
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        try:
            data = json.loads(line)
            
            # Xác định loại dữ liệu và serial number
            if "com_samsung_gmes2_mc_cmm_biz_ppd_vo_McNetworkModelInfoSVO" in data:
                serial = data["com_samsung_gmes2_mc_cmm_biz_ppd_vo_McNetworkModelInfoSVO"]["mcNetworkModelInfo01DVO"]["nmgNo"]
                model_info_dict[serial] = data
                current_serial = serial
                
            elif "com_samsung_gmes2_mc_cmm_biz_ppd_vo_McNetworkLoadInfoSVO" in data:
                serial = data["com_samsung_gmes2_mc_cmm_biz_ppd_vo_McNetworkLoadInfoSVO"]["McNetworkLoadInfo01DVO"]["packBoxNo"]
                box_info_dict[serial] = data
                
            elif "com_samsung_gmes2_pm_jsn_vo_PmProcInspResultJSONSVO" in data:
                serial = data["com_samsung_gmes2_pm_jsn_vo_PmProcInspResultJSONSVO"]["inputDVO"]["nmgNo"]
                inspection_dict[serial] = data
                
            elif "modelInfo" in data and current_serial:
                all_data_dict[current_serial] = data
                
        except json.JSONDecodeError:
            continue
            
except FileNotFoundError:
    print("gmes_api.json not found. Using default data.")
    
# Tạo dữ liệu mẫu nếu không có dữ liệu
if not model_info_dict:
    serial_base = "S51V2378"
    for i in range(40, 50):
        serial = f"{serial_base}{i}"
        model_code = f"SFG-BRR{i%10}Z4RGK{(i%3)+1}"
        basic_model_code = f"SFG-BRR{i%10}Z"
        
        # Tạo model info
        model_info_dict[serial] = {
            "com_samsung_gmes2_mc_cmm_biz_ppd_vo_McNetworkModelInfoSVO": {
                "mcNetworkModelInfo01DVO": {
                    "fctCode": FACTORY_CODE,
                    "plantCode": PLANT_CODE,
                    "nmgNo": serial
                },
                "mcNetworkModelInfo02DVO": [{
                    "modelCode": model_code,
                    "basicModelCode": basic_model_code,
                    "pbaPcs": f"0{(i%3)+1}-",
                    "pcbPcs": f"{i%3}" if i%3 else "-",
                    "prodcPlanYmd": f"2025{(i%12)+1:02d}{(i%28)+1:02d}"
                }],
                "anyframeDVO": {
                    "pageNo": "0",
                    "pageRowCount": "0"
                }
            }
        }
        
        # Tạo box info
        pack_box_no = f"CARP514Y22502{850+i}"
        box_info_dict[serial] = {
            "com_samsung_gmes2_mc_cmm_biz_ppd_vo_McNetworkLoadInfoSVO": {
                "McNetworkLoadInfo01DVO": {
                    "fctCode": FACTORY_CODE,
                    "plantCode": PLANT_CODE,
                    "packBoxNo": serial
                },
                "McNetworkLoadInfo02DVO": [{
                    "packBoxNo": pack_box_no,
                    "modelCode": model_code,
                    "erpSalOrdNo": f"12502056{80+i}",
                    "boxCode": f"EP69-016{40+i%10}A",
                    "pallCnstQty": f"{6+(i%5)}",
                    "pallPrtQty": "0",
                    "loadFloorNum": f"{1+(i%5)}",
                    "cartonCnstQty": "1",
                    "cartonPrtQty": "1"
                }],
                "anyframeDVO": {
                    "pageNo": "0",
                    "pageRowCount": "0"
                }
            }
        }
        
        # Tạo inspection results
        test_status = "Y" if i%4 != 0 else "N"
        inspection_dict[serial] = {
            "com_samsung_gmes2_pm_jsn_vo_PmProcInspResultJSONSVO": {
                "inputDVO": {
                    "fctCode": FACTORY_CODE,
                    "plantCode": PLANT_CODE,
                    "nmgNo": serial,
                    "workGubunCode": "ALL"
                },
                "outputDVOList": [{
                    "sn": serial,
                    "enb": "Y" if i%5 != 0 else "N",
                    "appearance": "Y" if i%6 != 0 else "N",
                    "mainTest": "Y" if i%7 != 0 else "N",
                    "pbaTest": "Y" if i%2 == 0 else "",
                    "airLeak": "Y" if i%8 != 0 else "N",
                    "testStatus": test_status
                }],
                "errorDVO": {
                    "error": "No error"
                },
                "anyframeDVO": {
                    "appName": "com.samsung.gmes2.pm.jsn.app.PmProcInspResultJSONApp",
                    "methodName": "getProcInspResult",
                    "inputSVOName": "com.samsung.gmes2.pm.jsn.vo.PmProcInspResultJSONSVO",
                    "clientIPAddr": f"107.107.80.{20+i%10}",
                    "pageNo": "0",
                    "pageRowCount": "0"
                }
            }
        }
        
        # Tạo all data
        model_info = model_info_dict[serial]["com_samsung_gmes2_mc_cmm_biz_ppd_vo_McNetworkModelInfoSVO"]["mcNetworkModelInfo02DVO"][0]
        box_info = box_info_dict[serial]["com_samsung_gmes2_mc_cmm_biz_ppd_vo_McNetworkLoadInfoSVO"]["McNetworkLoadInfo02DVO"][0]
        insp_info = inspection_dict[serial]["com_samsung_gmes2_pm_jsn_vo_PmProcInspResultJSONSVO"]["outputDVOList"][0]
        
        all_data_dict[serial] = {
            "modelInfo": model_info,
            "boxInfo": box_info,
            "inspectionResults": insp_info
        }

@app.route('/get_model_info', methods=['GET', 'POST'])
def get_model_info():
    """
    Giả lập API getModelInfo từ GMES
    """
    # Xử lý request dựa vào phương thức
    if request.method == 'GET':
        serial_number = request.args.get('serialNumber')
    else:  # POST
        data = request.get_json() or {}
        
        # Kiểm tra nếu body có cấu trúc giống SetMes.ModelInfo
        if "com_samsung_gmes2_mc_cmm_biz_ppd_vo_McNetworkModelInfoSVO" in data:
            svo = data["com_samsung_gmes2_mc_cmm_biz_ppd_vo_McNetworkModelInfoSVO"]
            if "mcNetworkModelInfo01DVO" in svo:
                serial_number = svo["mcNetworkModelInfo01DVO"].get("nmgNo")
        else:
            serial_number = data.get('serialNumber')
    
    if not serial_number:
        return jsonify({"error": "Missing serialNumber"}), 400
        
    # Tìm dữ liệu dựa trên serial number
    if serial_number in model_info_dict:
        return jsonify(model_info_dict[serial_number])
    
    # Trả về lỗi nếu không tìm thấy
    return jsonify({"error": "Serial number not found"}), 404

@app.route('/get_load_info', methods=['GET', 'POST'])
def get_load_info():
    """
    Giả lập API getLoadinfo từ GMES
    """
    # Xử lý request dựa vào phương thức
    if request.method == 'GET':
        serial_number = request.args.get('serialNumber')
    else:  # POST
        data = request.get_json() or {}
        
        # Kiểm tra nếu body có cấu trúc giống SetMes.GetBoxInfo
        if "com_samsung_gmes2_mc_cmm_biz_ppd_vo_McNetworkLoadInfoSVO" in data:
            svo = data["com_samsung_gmes2_mc_cmm_biz_ppd_vo_McNetworkLoadInfoSVO"]
            if "McNetworkLoadInfo01DVO" in svo:
                serial_number = svo["McNetworkLoadInfo01DVO"].get("packBoxNo")
        else:
            serial_number = data.get('serialNumber')
    
    if not serial_number:
        return jsonify({"error": "Missing serialNumber"}), 400
        
    # Tìm dữ liệu dựa trên serial number
    if serial_number in box_info_dict:
        return jsonify(box_info_dict[serial_number])
    
    # Trả về lỗi nếu không tìm thấy
    return jsonify({"error": "Serial number not found"}), 404

@app.route('/get_proc_insp_result', methods=['GET', 'POST'])
def get_proc_insp_result():
    """
    Giả lập API getProcInspResult từ GMES
    """
    # Xử lý request dựa vào phương thức
    if request.method == 'GET':
        serial_number = request.args.get('serialNumber')
    else:  # POST
        data = request.get_json() or {}
        
        # Kiểm tra nếu body có cấu trúc giống SetMes.GetALLEPASS
        if "com_samsung_gmes2_pm_jsn_vo_PmProcInspResultJSONSVO" in data:
            svo = data["com_samsung_gmes2_pm_jsn_vo_PmProcInspResultJSONSVO"]
            if "inputDVO" in svo:
                serial_number = svo["inputDVO"].get("nmgNo")
        else:
            serial_number = data.get('serialNumber')
    
    if not serial_number:
        return jsonify({"error": "Missing serialNumber"}), 400
        
    # Tìm dữ liệu dựa trên serial number
    if serial_number in inspection_dict:
        return jsonify(inspection_dict[serial_number])
    
    # Trả về lỗi nếu không tìm thấy
    return jsonify({"error": "Serial number not found"}), 404

@app.route('/set_insp_info', methods=['POST'])
def set_insp_info():
    """
    Giả lập API setInspInfo từ GMES
    """
    data = request.get_json() or {}
    
    # Kiểm tra nếu body có cấu trúc giống SetMes.Epass
    if "com_samsung_gmes2_mc_cmm_biz_ppd_vo_McNetworkInspInfoSVO" in data:
        svo = data["com_samsung_gmes2_mc_cmm_biz_ppd_vo_McNetworkInspInfoSVO"]
        if "McNetworkInspInfo01DVO" in svo:
            dvo = svo["McNetworkInspInfo01DVO"]
            serial_number = dvo.get("nmgNo")
            pass_yn = dvo.get("passYn")
            
            if not serial_number:
                return jsonify({"error": "Missing nmgNo"}), 400
                
            # Giả lập cập nhật dữ liệu
            response = {
                "com_samsung_gmes2_mc_cmm_biz_ppd_vo_McNetworkInspInfoSVO": {
                    "McNetworkInspInfo01DVO": {
                        "resultYn": "Y",
                        "resultMessage": f"GMES 검사정보 등록 완료({serial_number})",
                        **dvo
                    }
                }
            }
            
            return jsonify(response)
    
    # Nếu không có cấu trúc đúng
    return jsonify({"error": "Invalid request structure"}), 400

@app.route('/get_all_data', methods=['GET', 'POST'])
def get_all_data():
    """
    Trả về tất cả dữ liệu cho một serial number
    """
    # Xử lý request dựa vào phương thức
    if request.method == 'GET':
        serial_number = request.args.get('serialNumber')
    else:  # POST
        data = request.get_json() or {}
        serial_number = data.get('serialNumber')
    
    if not serial_number:
        return jsonify({"error": "Missing serialNumber"}), 400
        
    # Tìm dữ liệu dựa trên serial number
    if serial_number in all_data_dict:
        return jsonify(all_data_dict[serial_number])
    
    # Trả về lỗi nếu không tìm thấy
    return jsonify({"error": "Serial number not found"}), 404

@app.route('/', methods=['GET'])
def home():
    """
    Trang chủ với thông tin API
    """
    return jsonify({
        "name": "GMES Simulator API",
        "endpoints": [
            {"path": "/get_model_info", "methods": ["GET", "POST"], "description": "Get model info from serial number"},
            {"path": "/get_load_info", "methods": ["GET", "POST"], "description": "Get box info from serial number"},
            {"path": "/get_proc_insp_result", "methods": ["GET", "POST"], "description": "Get inspection results from serial number"},
            {"path": "/set_insp_info", "methods": ["POST"], "description": "Set inspection info for serial number"},
            {"path": "/get_all_data", "methods": ["GET", "POST"], "description": "Get all data for serial number"}
        ],
        "sample_serials": list(all_data_dict.keys())[:5]
    })

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
