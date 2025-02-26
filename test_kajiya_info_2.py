from lxml import html

def get_weapon_info(html_content, weapon_name):
    """
    指定されたHTMLコンテンツから、武器名を検索し、
    その位置（上から何番目か）と攻撃力を取得する関数。

    :param html_content: HTMLの文字列
    :param weapon_name: 探したい武器名
    :return: (武器の位置（1始まりのインデックス）, 攻撃力), 見つからない場合は (-1, None)
    """
    tree = html.fromstring(html_content)
    weapon_names = []
    weapon_attacks = []

    # 各ラジオボタンのあるセルを取得
    radio_cells = tree.xpath("//td[input[@type='radio']]")

    for cell in radio_cells:
        # 「名称」列はラジオボタンの次の td 要素
        name_td = cell.xpath("following-sibling::td[1]")
        attack_td = cell.xpath("following-sibling::td[2]")  # 攻撃力の列

        if name_td and name_td[0].text is not None:
            weapon_names.append(name_td[0].text.strip())
            attack = attack_td[0].text.strip() if attack_td and attack_td[0].text is not None else None
            weapon_attacks.append(attack)
        else:
            weapon_names.append("-")
            weapon_attacks.append(None)

    # 指定された武器のインデックスを取得（見つかった場合は 1始まりのインデックスに変換）
    try:
        index = weapon_names.index(weapon_name)
        position = index  # 1-based index
        attack_power = weapon_attacks[index]
    except ValueError:
        position = -1
        attack_power = None

    return position, attack_power


# テスト実行
html_content = """


<!DOCTYPE html>
<html lang="ja"><head>
<META HTTP-EQUIV="Content-type" CONTENT="text/html; charset=UTF-8">
<meta http-equiv="Content-Style-Type" content="text/css" />
<link rel="stylesheet" href="./html/Black2.css" type"text.css">
<title>ＦＦ ＢＡＴＴＬＥ</title>
<SCRIPT LANGUAGE="JavaScript">
<!--
var flag = 0;

function check() {
	if(flag == 0){ flag = 1; }
	else{ return false; }
}
//-->
</SCRIPT>
</head>
<body oncontextmenu="return false" onselectstart="return false">

	<h1>鍛冶屋</h1>
	<hr size=0>
	<p>
	<FONT SIZE=3>
	<B>職人風の男</B><BR>
	「客か・・・久しぶりだな。<BR>
		おい、ちょっとお前の装備よく見せてみろよ。<BR>
		・・・・・・こりゃひでえな。<BR>
		どうだ、俺に任せてみないか？」
	</FONT>
	<br><hr>現在の所持金：6.507293e+20 Ｇ<br>
		<center>
		<table><tr><td valign=top>

		<table>
		<tr>
		<form action=shop.cgi method=post onSubmit=return check()>
		<th></th><th></th><th>名称</th><th>攻撃力</th><th>価格</th><tr><td rowspan=2 class=b1><IMG src=https://kroko.jp/image//mini_ded.gif>
			<td class=b1><input type=radio name=kaizo value=item2><td class=b1>ロケット花火<td align=right class=b1>1024<td align=right class=b1>25
			<tr><td class=b1><input type=radio name=kaizo value=def2><td class=b1>-<td align=right class=b1>7.37869762948384e+23<td align=right class=b1>25,000,000,000<tr><td rowspan=2 class=b1><IMG src=https://kroko.jp/image//mini_mire_nia_hane.gif>
			<td class=b1><input type=radio name=kaizo value=item3><td class=b1>-<td align=right class=b1>0<td align=right class=b1>0
			<tr><td class=b1><input type=radio name=kaizo value=def3><td class=b1>AT<td align=right class=b1>9.35361047891776e+53<td align=right class=b1>25,000,000,000<tr><td rowspan=2 class=b1><IMG src=https://kroko.jp/image//iton.gif>
			<td class=b1><input type=radio name=kaizo value=item4><td class=b1>-<td align=right class=b1>0<td align=right class=b1>0
			<tr><td class=b1><input type=radio name=kaizo value=def4><td class=b1>ヴェール<td align=right class=b1>1.87072209578355e+54<td align=right class=b1>25,000,000,000</table>
		<td valign=top>
	
		<table>
		<tr><th></th><th>名称</th><th>鉱石の価値</th><tr><td class=b1><input type=radio name=kai value=1><td class=b1>火のルビー<td class=b1>20000000000000<tr><td class=b1><input type=radio name=kai value=2><td class=b1>火のルビー<td class=b1>20000000000000<tr><td class=b1><input type=radio name=kai value=3><td class=b1>火のルビー<td class=b1>20000000000000<tr><td class=b1><input type=radio name=kai value=4><td class=b1>火のルビー<td class=b1>20000000000000<tr><td class=b1><input type=radio name=kai value=5><td class=b1>白マテリア<td class=b1>2000000000000<tr><td class=b1><input type=radio name=kai value=6><td class=b1>白マテリア<td class=b1>2000000000000<tr><td class=b1><input type=radio name=kai value=7><td class=b1>白マテリア<td class=b1>2000000000000<tr><td class=b1><input type=radio name=kai value=8><td class=b1>白マテリア<td class=b1>2000000000000<tr><td class=b1><input type=radio name=kai value=9><td class=b1>白マテリア<td class=b1>2000000000000<tr><td class=b1><input type=radio name=kai value=10><td class=b1>白マテリア<td class=b1>2000000000000<tr><td class=b1><input type=radio name=kai value=11><td class=b1>白マテリア<td class=b1>2000000000000<tr><td class=b1><input type=radio name=kai value=12><td class=b1>白マテリア<td class=b1>2000000000000<tr><td class=b1><input type=radio name=kai value=13><td class=b1>白マテリア<td class=b1>2000000000000<tr><td class=b1><input type=radio name=kai value=14><td class=b1>白マテリア<td class=b1>2000000000000<tr><td class=b1><input type=radio name=kai value=15><td class=b1>白マテリア<td class=b1>2000000000000<tr><td class=b1><input type=radio name=kai value=16><td class=b1>白マテリア<td class=b1>2000000000000<tr><td class=b1><input type=radio name=kai value=17><td class=b1>白マテリア<td class=b1>2000000000000<tr><td class=b1><input type=radio name=kai value=18><td class=b1>白マテリア<td class=b1>2000000000000<tr><td class=b1><input type=radio name=kai value=19><td class=b1>白マテリア<td class=b1>2000000000000<tr><td class=b1><input type=radio name=kai value=20><td class=b1>白マテリア<td class=b1>2000000000000<tr><td class=b1><input type=radio name=kai value=21><td class=b1>白マテリア<td class=b1>2000000000000<tr><td class=b1><input type=radio name=kai value=22><td class=b1>白マテリア<td class=b1>2000000000000<tr><td class=b1><input type=radio name=kai value=23><td class=b1>白マテリア<td class=b1>2000000000000<tr><td class=b1><input type=radio name=kai value=24><td class=b1>白マテリア<td class=b1>2000000000000<tr><td class=b1><input type=radio name=kai value=25><td class=b1>白マテリア<td class=b1>2000000000000<tr><td class=b1><input type=radio name=kai value=26><td class=b1>白マテリア<td class=b1>2000000000000<tr><td class=b1><input type=radio name=kai value=27><td class=b1>邪のオブシダン<td class=b1>20000000000000<tr><td class=b1><input type=radio name=kai value=28><td class=b1>邪のオブシダン<td class=b1>20000000000000<tr><td class=b1><input type=radio name=kai value=29><td class=b1>邪のオブシダン<td class=b1>20000000000000</table>
		</table>
		</center><br><br>
		<input type=hidden name=id value=xxxxxxxx>
		<input type=hidden name=pass value=Spa9enG5p1>
		<input type=hidden name=mode value=saise>
		<input type=hidden name=check value=7>
		<input type=submit class=btn value=依頼する>
		</form><hr>

<table>
<tr><td width=40%>
<form action="ffadventure.cgi" method="post" onSubmit=return check()>
<input type=hidden name=id value=xxxxxxxx>
<input type=hidden name=pass value=Spa9enG5p1>
<input type=hidden name=mode value=log_in>
<input type=submit class=btn value="ステータス画面へ戻る">
</form><br>
<form action="./shopw.cgi" method="post" onSubmit=return check() style="padding-bottom: 10px;">
<input type=hidden name=id value=xxxxxxxx>
<input type=hidden name=pass value=Spa9enG5p1>
<input type=hidden name=mode value=item_shop>
<input type=submit class=btn value="武器屋へ行く">
</form>
<form action="./shopg.cgi" method="post" onSubmit=return check() style="padding-bottom: 10px;">
<input type=hidden name=id value=xxxxxxxx>
<input type=hidden name=pass value=Spa9enG5p1>
<input type=hidden name=mode value=def_shop>
<input type=submit class=btn value="防具屋へ行く">
</form>
<form action="./shopa.cgi" method="post" onSubmit=return check() style="padding-bottom: 10px;">
<input type=hidden name=id value=xxxxxxxx>
<input type=hidden name=pass value=Spa9enG5p1>
<input type=hidden name=mode value=acs_shop>
<input type=submit class=btn value="怪しい店へ行く">
</form>
<form action="./storagetop.cgi" method="post" onSubmit=return check() style="padding-bottom: 10px;">
<input type=hidden name=id value=xxxxxxxx>
<input type=hidden name=pass value=Spa9enG5p1>
<input type=hidden name=mode value=log_in>
<input type=submit class=btn value="倉庫へ行く">
</form>
<form action="./auctiontop.cgi" method="post" onSubmit=return check() style="padding-bottom: 10px;">
<input type=hidden name=id value=xxxxxxxx>
<input type=hidden name=pass value=Spa9enG5p1>
<input type=hidden name=mode value=auction>
<input type=submit class=btn value="オークション会場へ行く">
</form>
<form action=./shop.cgi method=post onSubmit=return check() style="padding-bottom: 10px;">
<input type=hidden name=mode value=kajiya>
<input type=hidden name=id value=xxxxxxxx>
<input type=hidden name=pass value=Spa9enG5p1>
<input type=submit class=btn value=鍛冶屋へ行く>
</form>
</td>
<td valign=top>


</td>
</tr>
</table>

</body></html>

"""

# テスト
weapon_to_find = "ヴェール"
print(get_weapon_info(html_content, weapon_to_find))