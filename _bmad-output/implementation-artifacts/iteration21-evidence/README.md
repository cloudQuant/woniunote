# 迭代 21 脱敏验收证据

整体状态为 **INCOMPLETE**。当前结果和剩余门禁以 [开发与验收记录](../../planning-artifacts/迭代21-开发与验收记录.md) 为准。

本目录保留主线程已读回的 JSON 摘要、源码清单和 SHA256，便于审阅时核对。[index.json](index.json) 记录各文件的原始路径和摘要。原始日志、浏览器 trace、运行配置及凭据留在受限临时目录，不复制到仓库。

各文件对应不同检查阶段。`g1-negative-supplement.json` 中当时的缺口由后续 `g1-final-incremental-index.json` 和 `runner-term-upload-r5.json` 补充；不改写历史结果。`frontend-final12-root-checks.json` 保留覆盖率门禁失败，`frontend-final13-root-checks.json` 记录补充行为测试后的通过结果。两快照仅有 4 个测试文件变化，产品和构建输入未改变，详见 `frontend-final12-to13-delta.json`。真实 Chromium 摘要是测试变体的 4 条认证流程，不能替代正式验证码或 D04 跨版本业务演练。

`frontend-final14-mock-root.json` 保留严格隔离 gate 的失败：257 项通过、5 项失败、2 项既有豁免，服务拒绝 5 次未被 mock 接管的请求。`functional13-real-root.json` 及对应源码清单保留新增真实业务首轮失败，认证与训练通过不能替代尚未跑完的草稿发布和评论链路；后续修复必须另附冻结候选的完整复验。

后端候选 3 的源码和构建证据、前端冻结快照与最终 Git 提交是不同标识。当前工作区尚未提交或推送，也没有候选远端 CI、生产部署或发行结论。

`environment-recovery.json` 记录旧临时目录和句柄不可用的事实；mock15 终态为 UNVERIFIED，不能由记忆补写。新原始日志改存用户缓存下的私有验收目录。`frontend16-root-summary.json` 记录完整四项目 262 通过、2 项既有豁免及零请求隔离违规，包含 264 个已关闭 context 的摘要哈希；`functional16-root-failure.json` 保留真实 HTTP 的 60 通过/1 失败，失败为 UEditor 重复 Content-Type，后续迁移与真实浏览器未执行。后端候选4的修复结果将独立追加。
# 2026-10-24 候选 4 / source17 增量

`backend4-mac-checks.json` 与 `formal-negative-macos4.json` 保存 MIME 修复后的
Mac 正式/测试构建、各 7 项 CTest 和正式注入路由负测。`backend-source4-manifest.json`
绑定其编译输入；这些结果不适用于后续封面修改的候选 5。

`source-17-manifest.json` 和 `functional17-root-failure.json` 保留 HTTP 61/61、真实
Chromium 5/6 的阶段结果。失败发生于上传后保存草稿：旧 thumbnail 字段过短返回 500，
后续发布和评论投票未执行。整体继续为 INCOMPLETE；不得覆盖该失败历史。

## 2026-10-24 候选 5 / source18–20 增量

新增52份脱敏文件，索引共86份。既有34份摘要保持原哈希；不复制原始日志、运行配置、业务正文或浏览器trace。

- `backend-source5-manifest.json`、`backend5-*-checks.json` 绑定封面修复后的构建输入：Mac两变体及Linux两路径四变体均构建通过，每个CTest为8/8；`formal-negative-*5.json` 单列正式构建默认/注入环境的测试路由404证据。
- `frontend18-root-checks.json` 记录Node22.13.0、627单元和质量门禁。`source18-mac-real-root.json` 与 `frontend18-mock-failure-summary.json` 保留导航超时与缺少thumbnail fixture的失败，后续成功不覆盖历史。
- `source19-real-summary.json` 记录测试变体HTTP63/63与真实Chromium6/6，包括完整封面业务链。`source19-linux5-primary-summary.json`、两组 `linux5-*-test-summary.json` 及runtime/migration/transport文件记录两Linux路径各63/63、迁移、真实COMMIT/Redis故障触发与制品身份。
- `runner-term-upload-source19.json` 记录双实例真实上传/数据隔离及只向runner主PID发TERM的清理。`source20-primary-evidence-verification.json` 单列主线程对日志、二进制、源码及精确资源归属的独立读回。
- `source20-mock-full-summary.json` 记录四项目262通过、0失败、2项既有移动hover豁免，以及264个context全部关闭、归属齐全和零隔离违规。两个delta文件解释哪些是测试入口/fixture变化，不能将不同快照混为一个Git提交。

原始证据在用户缓存 `/Users/yunjinqi/.cache/woniunote-iter21/acceptance-20261024/` 下受限保存。正式视觉验证码、D04业务升级/回滚、最终CI与独立终审尚未完成；此目录不是整体验收通过或生产上线证明。

## 2026-10-24 G1 补证与 source21 失败增量

本次追加9份脱敏摘要，索引共95份；此前86份保留原哈希。

- `source20-preflight-negatives.json` 记录当前runner的12项拒绝用例；静态检查及其主线程读回分别记录在 `source20-static-root-checks.json` 和 `source20-preflight-static-primary-verification.json`。
- `source20-service-negatives-and-rate-limit.json` 保留 MySQL/Redis 启动失败、坏配置拒绝的通过，以及原正式变体检查器误判导致的整体 INCOMPLETE。`source20-formal-confirmation.json` 是单独复验：health先通过，测试挑战门禁拒绝，实际退出2，未进入业务测试；不反推原运行退出码或404。`source20-default-rate-limit.json` 单独记录默认60/min下真实429/Retry-After用例1/1。
- `source21-g1-projection-readback.json` 绑定上述摘要、日志、runner及二进制，精确11个run标签的容器/volume均为0。它也保留两次定向补测：先是驱动命令错误，后是system-libs两项评论通过、资料投影准备账号注册503；vcpkg和迁移未运行。两个子进程的精确退出码未持久化，不能从driver非零倒推。
- `d04-original-handoff-and-upload-failure.json` 记录用户完成原始版登录、草稿article1的UI与数据库摘要，以及Nginx临时目录权限造成上传500。`backend6-auth-primary-source-review.json` 仅是新增认证专属Redis client和时限测试的源码复核，构建与运行仍待独立证据。

这些结果闭合当前runner在指定候选5上的补测范围；候选6的正式注入负测及业务回归仍待完成，AC21-00/I21-G1尚不整体关闭。原始版视觉登录也不替代候选版正式流程或D04跨版本恢复。

随后追加 `d04-original-upload-repair-readback.json`，索引共96份。专属Nginx两处临时路径修复后，UI上传及HTTPS 200/image/png/10491字节的原文件、落盘、HTTP三方SHA一致；后端未重启，runtime/config/key权限保持。草稿重存后HTML字节经编辑器规范化，已记录最新摘要及可见正文不变；原始版本的thumbnail更新仍未持久化，不能把成功上传解释为封面业务已通过。维护备份、迁移和候选切换均NOT_RUN。

## 2026-10-24 source22 / 候选6首次真实HTTP

追加source22清单、差异及`source22-mac6-primary-summary.json`，索引共99份。macOS真实HTTP为66通过/1失败/0跳过，整体退出1；新增投影用例的25字符头像fixture超出现有VARCHAR(20)，保存资料500，完整投影断言未完成。四项Redis丢/迟确认通过，三个迟回复本地回调约1500ms，不能据此宣称远端命令已取消。精确run标签容器和volume均清理为0。二进制来源为backend-source6，前端仍源自source20；source22未复制候选5二进制，也未运行浏览器。


## 2026-10-24 source23 / 候选6补证与D04 stage

追加16份脱敏文件后索引共115份。六构建变体及各8/8 CTest、三正式制品默认/注入负测、source23两Linux各67/67和迁移、Mac投影及真实Chromium6/6已由主线程读回。`source23-primary-runtime-readback.json`保留命令、制品/结果哈希、Redis实际本地回调计时和五个run的精确资源清理；Mac浏览器前HTTP只运行投影1项，不冒充完整67项重跑。正式runner按预期退出2，未进入业务测试。

D04冻结清单及pre-asset/pre-exec-mode版本均保留。真实stage暴露发布脚本不可执行，mode-only修复后两个stage通过；失败目录在VM中按原commit保留，原业务服务未停止。两个候选前端相同且包含独立声明的70张PNG覆盖层；尚未完成实机应用构建、备份恢复、迁移、升级/回滚。候选2是兼容回退基线，其认证等待旧行为不代表最终候选6时限验收通过。

AC21-00/04/11/12与I21-G1可按记录的隔离范围关闭；正式候选视觉流程、D04跨版本数据与编辑恢复、远端CI/独立终审仍未完成，整体保持INCOMPLETE。

## 2026-10-24 D04 实机预构建与首次维护迁移

追加11份脱敏摘要，索引共126份。两候选在同一Ubuntu VM内的真实Node22.13/Vite/CMake Release构建通过，两个前端dist的315个文件字节一致；候选3正式二进制与Linux system-libs正式候选6一致。此阶段仅预构建，不等于部署完成。

`d04-maintenance-failure-analysis.json`保留配置占位、mysqldump选项和AppArmor目录限制的失败与修正。原始专属服务已按二进制身份停止；候选运行配置承接原DB/Redis/JWT及实际上传路径，TLS复用原隔离证书。`d04-backup-restore-primary-readback.json`记录完整13表备份在独立socket-only MySQL恢复后结构/行数/草稿和指定上传图像一致，临时进程退出，原MySQL PID738未变；未修改全局AppArmor。

`d04-first-maintenance-migrations-primary.json`记录两条已审SQL均退出0：答案列为DOUBLE NULL，封面列为VARCHAR(512)。13表行数和逐表数据摘要、草稿及真实上传图片均保持，评论迁移预检canonical_only且零阻塞/零计数差异，未执行comment votes apply。首次候选安装正在独立执行；正式视觉登录及跨版本恢复尚未通过。

## 2026-10-24 正式候选首次安装与双向页面预检

首次安装及正式路由负测3份摘要、实际业务基线与预检读回3份摘要已归档，索引共132份。用户完成候选2的正式验证码登录；页面实际写入训练小数1.25/跳过NULL、article2封面和正文、评论及投票。双向混合前后端均能读取受保护资料并写评论；独立DB读回三条评论、旧投票和训练答案，上传图像HTTPS与磁盘SHA一致。正式候选2退出HTTP200，用户2的Redis会话槽随后不存在。

`d04-cross-candidate-progress.json`保留临时预检源binary权限guard的安全失败及修正，旧临时候选3unit已停止，Nginx已恢复原哈希，主候选2仍运行。预检尚缺真实跨版本refresh，未签发全PASS兼容记录；升级/回滚/再升级和编辑恢复继续INCOMPLETE。两个前端dist字节一致，不能替代不同hash资源保留的独立r4证据。

## 2026-10-24 最终 source10 / source24 / D04 candidate4 增量

本阶段索引共194份；各旧记录保持原始摘要，新增阶段失败单列。

- `backend-source10-*`、`backend10-primary-build-readback.json`绑定最终后端：Mac、Linux系统库、Linux vcpkg正式/测试六变体均构建通过，各CTest 8/8。首次Linux命令携带旧预期摘要而拒绝、正式负测检查器用错health路径均保留，不归为产品通过。
- `source24-final-runtime-summary.json`及三份root/结果文件绑定三路径各71项HTTP和独立迁移，Mac另有真实Chromium6/6。两个资源readback文件独立验证4个run归属容器/卷为零、loopback端口关闭，不依赖manifest清理前running状态。
- `final-review-current-local-summary.json`是当时阶段快照；其“Linux/D04进行中”由本节后续结果覆盖。最终648单元、四项原覆盖率门槛、lint/build与官方registry audit通过；`source24-frontend-quality-binding.json`验证对应产品/单元输入未变。
- `source25-mock-failure-summary.json`保留252通过/10失败/2既有豁免与8次preview拒绝；mock修复前不填写G3通过，也不以source20历史成功代替当前复验。
- `d04-final4-cycle-primary-readback.json`和readback文件记录真实3→4升级、新标题写入、回滚3、恢复同一4制品，八类业务数据与上传字节不变；正式退出HTTP200且Redis会话槽不存在。之前2/3重新发布循环、首次维护完整备份恢复和迁移证据继续有效。
- `d04-final4-compatibility-evidence.json`明确最终4仅对字节相同的认证组件复用实际过期刷新证据；最终4实际混合组合写入、编辑恢复、发布/回滚及退出均单独观察。不声称最终4重复新验证码或强制过期测试。

当前剩余项为完整四浏览器mock修复复验、最终静默catch门禁与远端CI。主仓未提交或推送，整体INCOMPLETE。受限原始日志/截图仍在本机缓存；不得向仓库复制真实运行配置、密码、数据库备份或浏览器trace。

追加最终静默catch与独立复核记录后索引共199份。`final-frontend-quality-binding.json`明确排除已改的静态检查器，360条产品/单元等路径仍与source24一致；该检查器单独复验0违规。source26只含E2E和检查器变化，lint通过，尚未运行完整矩阵；移动端既有深链用例的编辑器DOM缺失仍在定点诊断，不能将此前source25成功倒推为当前通过。

追加source27源码清单、首轮收集失败及依赖隔离记录后索引共202份。首轮因共享node_modules导致Playwright实例路径混用，退出1且未执行用例；只移除source27自己的依赖符号链接并按原锁文件独立npm ci，锁文件摘要保持。完整四项目复验另行记录，不能把依赖安装成功写作功能通过。

source27独立依赖后的完整四项目复验为260通过/2失败/2既有移动hover豁免，workers1、retries0；两个失败均为Firefox/WebKit深链登录后的编辑器DOM缺失。264个context全部关闭、归属完整、违规0，preview拒绝0；此前测试读取收尾问题已消除，A21-33产品初始化修复及最终复验仍待完成。新增root和失败摘要后索引共204份。

source28 增量：已归档编辑器受控基线失败/修复四项目通过摘要、430 文件最终清单、独立依赖、lint、真实后端 6 项及清理读回；HTTP 本次仅重跑 health（1项），既有 71 项范围见 source24。新增候选5仅冻结/传入，尚未代表发布完成。当前索引 215 份，完整 mock 与 D04 增量结果后续单列。

最终本地结果入口：`final-local-acceptance-summary.json`（source28 430文件、完整mock266/0/2、268context零违规、真实UI6/6、D04 candidate5实际升级回滚与同制品恢复）。G1–G4本地PASS；整体INCOMPLETE，G5远端CI未运行。最终索引231份；旧失败、依赖收集失败及修复阶段证据保留。原始日志/trace/配置/截图不入仓，账号密码不进入交付证据。

最终待提交源码入口：`source-29-manifest.json`与`source29-whitespace-artifact-binding.json`。source29仅删除7个文件的EOF空行，其余423个输入不变；重建315个前端产物与source28字节一致，沿用既有功能与D04证据。`final-local-acceptance-summary.json`保留为清理前的功能验收记录。提交清单检查另见`final-private-index-hygiene.json`，最终索引234份；主索引保持空，G5远端CI仍未执行。

远端只读预检：`remote-ci-readonly-preflight.json`确认GitHub基线及候选分支/PR空缺，并发现origin双推送配置；后续请求改为仅使用github remote。此记录不代表推送或CI通过，最终索引235份。

首轮远端CI：PR #1 / head dc4ce0e / run 40073471951，三项通过、三项失败；C++8/8、前端648通过，cppcheck局部命名遮蔽、runner缺rg、WebKit竞争用例超出原5秒窗口均保留在ci-run-40073471951-summary.json。ci-first-fixes-primary-review.json记录三项最小修正和本地四项目定向4/4、隔离零违规；不冒充完整远端复验。当前索引237份，G5仍FAIL/INCOMPLETE。

后续远端CI：新增run 40074751399、40075774716两轮完整摘要及ci-race-and-shutdown-primary-review.json，索引240份全部SHA核对。业务HTTP71/迁移/UI6通过与限流清理Abort分开记录；旧runner未传播异常退出不得记为正常。候选2fb3791第四轮复验中，G5仍INCOMPLETE。

第四轮40077255747：完整mock266/0/2已通过；functional后端TERM0，rate-limit后端TERM134触发真实失败。ci-run-40077255747-summary.json记录allocator分类但不推断根因；ci-sanitizer-diagnostic-primary-review.json仅为条件诊断的静态/合成验证。当前索引242份，全部SHA核对，实际sanitizer及G5未通过。
