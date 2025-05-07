import requests
import json
import sys

# URL cơ sở
BASE_URL = "http://127.0.0.1:5000"

# Mặc định serial number để test
DEFAULT_TEST_SERIALS = ["S51V237829", "S51V237830", "S51V237831"]

print("=== GMES API TEST ===")
print(f"Kết nối đến: {BASE_URL}")
print("Chú ý: Đảm bảo rằng bạn đã chạy gmes_simulator.py trong một terminal riêng biệt!")

# Lấy danh sách serial number mẫu từ API home
available_serials = DEFAULT_TEST_SERIALS
try:
    print("\nĐang kết nối đến server...")
    response = requests.get(f"{BASE_URL}/", timeout=3)
    home_data = response.json()
    sample_serials = home_data.get("sample_serials", [])
    
    if sample_serials:
        available_serials = sample_serials
        print(f"Kết nối thành công! Lấy được {len(sample_serials)} serial mẫu.")
        print("Các serial mẫu có sẵn:")
        for i, serial in enumerate(available_serials):
            print(f"   {i+1}. {serial}")
    
except requests.exceptions.ConnectionError:
    print(f"Lỗi: Không thể kết nối đến {BASE_URL}")
    print("Vui lòng đảm bảo rằng gmes_simulator.py đã được chạy trong một terminal riêng biệt.")
except Exception as e:
    print(f"Lỗi khác khi kết nối: {str(e)}")

# Cho phép nhập serial number
print("\nNhập serial number để test (để trống để sử dụng serial mẫu đầu tiên):")
user_serial = input("> ").strip()

if not user_serial:
    test_serial = available_serials[0] if available_serials else DEFAULT_TEST_SERIALS[0]
    print(f"Sử dụng serial mẫu: {test_serial}")
else:
    test_serial = user_serial
    print(f"Sử dụng serial đã nhập: {test_serial}")

# Hàm để thực hiện request an toàn
def safe_request(method, url, **kwargs):
    try:
        if method.lower() == 'get':
            return requests.get(url, timeout=5, **kwargs)
        else:
            return requests.post(url, timeout=5, **kwargs)
    except requests.exceptions.RequestException as e:
        print(f"Lỗi khi gửi request đến {url}: {str(e)}")
        return None

# Hiển thị menu lựa chọn API để test
print("\nChọn API để test:")
print("1. get_model_info - Lấy thông tin model")
print("2. get_load_info - Lấy thông tin box")
print("3. get_proc_insp_result - Lấy kết quả kiểm tra")
print("4. set_insp_info - Thiết lập thông tin kiểm tra")
print("5. get_all_data - Lấy tất cả dữ liệu")
print("0. Chạy tất cả các API test")

choice = input("\nNhập lựa chọn của bạn (0-5): ").strip()

# Hàm test các API
def test_get_model_info():
    print("\n1. Test API get_model_info:")
    # Test GET request
    response_get = safe_request('get', f"{BASE_URL}/get_model_info", params={"serialNumber": test_serial})
    if response_get:
        print(f"GET Response Status: {response_get.status_code}")
        print(json.dumps(response_get.json(), indent=2))

    # Test POST request
    payload = {"serialNumber": test_serial}
    response_post = safe_request('post', f"{BASE_URL}/get_model_info", json=payload)
    if response_post:
        print(f"POST Response Status: {response_post.status_code}")
        print(json.dumps(response_post.json(), indent=2))

def test_get_load_info():
    print("\n2. Test API get_load_info:")
    # Test GET request
    response_get = safe_request('get', f"{BASE_URL}/get_load_info", params={"serialNumber": test_serial})
    if response_get:
        print(f"GET Response Status: {response_get.status_code}")
        print(json.dumps(response_get.json(), indent=2))

    # Test POST request
    payload = {"serialNumber": test_serial}
    response_post = safe_request('post', f"{BASE_URL}/get_load_info", json=payload)
    if response_post:
        print(f"POST Response Status: {response_post.status_code}")
        print(json.dumps(response_post.json(), indent=2))

def test_get_proc_insp_result():
    print("\n3. Test API get_proc_insp_result:")
    # Test GET request
    response_get = safe_request('get', f"{BASE_URL}/get_proc_insp_result", params={"serialNumber": test_serial})
    if response_get:
        print(f"GET Response Status: {response_get.status_code}")
        print(json.dumps(response_get.json(), indent=2))

    # Test POST request
    payload = {"serialNumber": test_serial}
    response_post = safe_request('post', f"{BASE_URL}/get_proc_insp_result", json=payload)
    if response_post:
        print(f"POST Response Status: {response_post.status_code}")
        print(json.dumps(response_post.json(), indent=2))

def test_set_insp_info():
    print("\n4. Test API set_insp_info:")
    # Tạo dữ liệu cho setInspInfo
    current_date = "20250214"
    current_time = "123000"
    payload = {
        "com_samsung_gmes2_mc_cmm_biz_ppd_vo_McNetworkInspInfoSVO": {
            "McNetworkInspInfo01DVO": {
                "fctCode": "C5H0A",
                "plantCode": "P514",
                "nmgNo": test_serial,
                "workGubunCode": "APPEARANCE",
                "inspGubunCode": "INSPINFO",
                "inspYmd": current_date,
                "inspDt": current_date + current_time,
                "passYn": "Y",
                "inspPrior": "1"
            },
            "anyframeDVO": {
                "appName": "com.samsung.gmes2.mc.cmm.app.McNetworkInfoApp",
                "methodName": "setInspInfo",
                "inputSVOName": "com.samsung.gmes2.mc.cmm.biz.ppd.vo.McNetworkMcNetworkInspInfoSVO"
            }
        }
    }
    response_post = safe_request('post', f"{BASE_URL}/set_insp_info", json=payload)
    if response_post:
        print(f"POST Response Status: {response_post.status_code}")
        print(json.dumps(response_post.json(), indent=2))

def test_get_all_data():
    print("\n5. Test API get_all_data:")
    # Test GET request
    response_get = safe_request('get', f"{BASE_URL}/get_all_data", params={"serialNumber": test_serial})
    if response_get:
        print(f"GET Response Status: {response_get.status_code}")
        print(json.dumps(response_get.json(), indent=2))

    # Test POST request
    payload = {"serialNumber": test_serial}
    response_post = safe_request('post', f"{BASE_URL}/get_all_data", json=payload)
    if response_post:
        print(f"POST Response Status: {response_post.status_code}")
        print(json.dumps(response_post.json(), indent=2))

# Thực hiện test dựa trên lựa chọn
if choice == '0':
    test_get_model_info()
    test_get_load_info()
    test_get_proc_insp_result()
    test_set_insp_info()
    test_get_all_data()
elif choice == '1':
    test_get_model_info()
elif choice == '2':
    test_get_load_info()
elif choice == '3':
    test_get_proc_insp_result()
elif choice == '4':
    test_set_insp_info()
elif choice == '5':
    test_get_all_data()
else:
    print("Lựa chọn không hợp lệ. Kết thúc test.")
    sys.exit(1)

print("\nTất cả các test đã hoàn thành!")
print("\nHướng dẫn: Để test với serial number khác, vui lòng chạy lại chương trình.")
