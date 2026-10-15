# HAProxy语法高亮

`haproxy.json`是供Shiki加载的TextMate语法，注册名称为`haproxy`，`scopeName`为`source.haproxy-configuration`。源码阅读器根据`ops/haproxy/*.cfg`路径选择该语言。

## 上游来源

- 维护组织：HAProxy Technologies，仓库`haproxytech/haproxy-atom-syntax`。
- 固定提交：`21d17d1c3710bedc68100935dd810e04634da04c`，提交时间`2020-10-13T12:57:41Z`。
- 源文件：[固定提交的haproxy.cson](https://github.com/haproxytech/haproxy-atom-syntax/blob/21d17d1c3710bedc68100935dd810e04634da04c/haproxy.cson)。原文件38,389字节、112条顶层规则。
- 原文件SHA-256：`9b3a65e92da33ff0f56a6f3b111e1306c6c2212bf898868c70c6912344a8a533`。
- 上游范围：[README](https://github.com/haproxytech/haproxy-atom-syntax/blob/21d17d1c3710bedc68100935dd810e04634da04c/README.md)说明支持HAProxy 2.3及HAProxy Enterprise 2.1，原语法名称为`HAProxy/HAPEE LB`。
- 许可：[上游LICENSE.md](https://github.com/haproxytech/haproxy-atom-syntax/blob/21d17d1c3710bedc68100935dd810e04634da04c/LICENSE.md)声明Apache-2.0。版权声明和[Apache License 2.0全文](https://www.apache.org/licenses/LICENSE-2.0.txt)共同保存在[LICENSE.haproxy.txt](LICENSE.haproxy.txt)。

## 转换与内容检查

2026-09-26使用第三方`cson-parser@4.0.9`解析固定提交的CSON，检查转换结果后通过文件编辑工具保存JSON。CSON parser仅用于这次转换与核对，网页运行时直接读取JSON。

本地调整为：`name`改为`haproxy`；增加`displayName`保存上游名称；增加`comment`记录来源、版权与调整内容。`patterns`、`captures`、全部正则表达式、规则顺序、`fileTypes`、折叠标记和`scopeName`均保留上游值。核对时逐字段比较解析后的结构，112条规则完全一致。

语法包括配置段名称、指令、ACL及条件、服务器和后端名称、地址与端口、时间和数量、字符串、路径及注释。高亮结果用于阅读源码，HAProxy配置的运行检查仍由对应部署流程执行。

## Shiki注册

JSON对象可以直接传给Shiki的`langs`或`loadLanguage`，高亮时指定`lang: 'haproxy'`。当前配套版本为Shiki 4.4.3；JSON中的`comment`保留第三方归属和调整声明，发布源文件时同时保留本目录的许可证。

## 验证记录

2026-09-26使用Shiki 4.4.3和`github-light`主题，读取阶段09固定源码中的`ops/haproxy/runtime.cfg`与`ops/haproxy/replicas.cfg`。两份配置均完成45行token化，拼接全部token后与原始源码完全一致；配置段、指令、服务器名称及数字等返回对应的HAProxy scope与主题颜色。

同时检查原始CSON的SHA-256、112条规则和其余原始字段；本地许可证与上游版权声明加Apache-2.0全文逐字核对通过，核对时仅统一空白字符。
