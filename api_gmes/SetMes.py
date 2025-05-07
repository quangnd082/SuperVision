import json
import requests


class SetMes:
    def __init__(self):
        self.User = "NWJSONIFID"
        self.Password = "8f4ad20b71d33d30479854645fd1728c71d4af33f619caead32655f376622bad"
        # self.Domain = "http://168.219.108.30:81/gmes2/gmes2If.do"
        self.Domain = "http://107.107.161.44:81/gmes2/gmes2If.do"
        self.FactoryCode = "C5H0A"
        self.PlantCode = "P514"

    def ModelInfo(self, nmg_no):
        frame = {
            "appName": "com.samsung.gmes2.mc.cmm.app.McNetworkInfoApp",
            "methodName": "getModelInfo",
            "inputSVOName": "com.samsung.gmes2.mc.cmm.biz.ppd.vo.McNetwork.McNetworkModelInfoSVO"
        }
        
        dvo = {
            "fctCode": self.FactoryCode,
            "plantCode": self.PlantCode,
            "nmgNo": nmg_no
        }
        
        svo = {
            "anyframeDVO": frame,
            "mcNetworkModelInfo01DVO": dvo
        }
        
        root = {
            "com_samsung_gmes2_mc_cmm_biz_ppd_vo_McNetworkModelInfoSVO": svo
        }
        
        contents = json.dumps(root)
        
        res = self.http_send(contents, "com_samsung_gmes2_mc_cmm_biz_ppd_vo_McNetworkModelInfoSVO", "mcNetworkModelInfo02DVO")
        
        if not res or len(res) != 1:
            return None
        
        return res[0]
    
    def GetBoxInfo(self, nmg_no):
        frame = {
            "appName": "com.samsung.gmes2.mc.cmm.app.McNetworkInfoApp",
            "methodName": "getLoadinfo",
            "inputSVOName": "com.samsung.gmes2.mc.cmm.biz.ppd.vo.McNetworkLoadInfoSVO"
        }
        
        dvo = {
            "fctCode": self.FactoryCode,
            "plantCode": self.PlantCode,
            "packBoxNo": nmg_no
        }
        
        svo = {
            "anyframeDVO": frame,
            "McNetworkLoadInfo01DVO": dvo
        }
        
        root = {
            "com_samsung_gmes2_mc_cmm_biz_ppd_vo_McNetworkLoadInfoSVO": svo
        }
        
        contents = json.dumps(root)
        
        res = self.http_send(contents, "com_samsung_gmes2_mc_cmm_biz_ppd_vo_McNetworkLoadInfoSVO", "McNetworkLoadInfo02DVO")
        
        if res is None:
            return None
        
        return res[0]
    
    def Epass(self, nmg_no, date, time, pass_yn):
        if self.ModelInfo(nmg_no) is None:
            return None
        
        frame = {
            "appName": "com.samsung.gmes2.mc.cmm.app.McNetworkInfoApp",
            "methodName": "setInspInfo",
            "inputSVOName": "com.samsung.gmes2.mc.cmm.biz.ppd.vo.McNetworkMcNetworkInspInfoSVO"
        }
        
        dvo = {
            "fctCode": self.FactoryCode,
            "plantCode": self.PlantCode,
            "nmgNo": nmg_no,  # S513600028
            "workGubunCode": "APPEARANCE",
            "inspGubunCode": "INSPINFO",
            "inspYmd": date,
            "inspDt": date + time,
            "passYn": pass_yn,
            # "bcrIp": "NONE",
            "inspPrior": "1",
            # "fstRegerId": "M01"
        }
        
        svo = {
            "anyframeDVO": frame,
            "McNetworkInspInfo01DVO": dvo
        }
        
        root = {
            "com_samsung_gmes2_mc_cmm_biz_ppd_vo_McNetworkInspInfoSVO": svo
        }
        
        contents = json.dumps(root)
        
        res = self.http_send(contents, "com_samsung_gmes2_mc_cmm_biz_ppd_vo_McNetworkInspInfoSVO", "McNetworkInspInfo01DVO")
        
        if res:
            return res
        return None
    
    def GetALLEPASS(self, nmg_no):
        """
        if self.ModelInfo(nmg_no) is None:
            return None
        """
        
        frame = {
            "appName": "com.samsung.gmes2.pm.jsn.app.PmProcInspResultJSONApp",
            "methodName": "getProcInspResult",
            "inputSVOName": "com.samsung.gmes2.pm.jsn.vo.PmProcInspResultJSONSVO",
            "pageNo": "0",
            "pageRowCount": "0"
        }
        
        dvo = {
            "fctCode": self.FactoryCode,
            "plantCode": self.PlantCode,
            "nmgNo": nmg_no,
            "workGubunCode": "ALL"
        }
        
        svo = {
            "anyframeDVO": frame,
            "inputDVO": dvo
        }
        
        root = {
            "com_samsung_gmes2_pm_jsn_vo_PmProcInspResultJSONSVO": svo
        }
        
        contents = json.dumps(root)
        
        res = self.http_send(contents, "com_samsung_gmes2_pm_jsn_vo_PmProcInspResultJSONSVO", "outputDVOList")
        
        if res is None:
            return None
        
        return res[0]
    
    def http_send(self, body, svo, dvo):
        try:
            headers = {
                "Accept": "application/json",
                "j_username": self.User,
                "j_password": self.Password
            }
            
            response = requests.post(self.Domain, data=body, headers=headers)
            
            if response.status_code != 200:
                self._error()
            
            response_text = response.text
            print(response_text)
            
            obj = json.loads(response_text)
            res = obj.get(svo, {}).get(dvo)
            
            if res is None:
                self._error()
            
            return res
        except Exception as e:
            print(f"Error: {str(e)}")
            raise
        
        return None
    
    def _error(self):
        raise Exception("잘못된 Serial Number 입력")
    
    def GetAllDomainData(self, nmg_no):
        """
        Get all available data for a specific serial number
        """
        all_data = {}
        
        # Get model information
        model_info = self.ModelInfo(nmg_no)
        if model_info:
            all_data["modelInfo"] = model_info
        
        # Get box information
        box_info = self.GetBoxInfo(nmg_no)
        if box_info:
            all_data["boxInfo"] = box_info
        
        # Get all inspection results
        inspection_results = self.GetALLEPASS(nmg_no)
        if inspection_results:
            all_data["inspectionResults"] = inspection_results
        
        return all_data
    
if __name__ == "__main__":
    mes = SetMes()
    
    # Example serial number - replace with actual serial number
    serial_number = "S513600028"  
    
    try:
        # Get all data for a specific serial number
        all_data = mes.GetAllDomainData(serial_number)
        print(json.dumps(all_data, indent=2))
        
        # Or get specific data
        model_info = mes.ModelInfo(serial_number)
        # box_info = mes.GetBoxInfo(serial_number)
        # inspection_results = mes.GetALLEPASS(serial_number)
    except Exception as e:
        print(f"Error: {str(e)}")
