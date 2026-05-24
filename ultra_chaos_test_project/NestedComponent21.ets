/**
 * 嵌套组件文件 - 深度 21
 */

import { NestedComponent22 } from './NestedComponent22';

@Component
export struct NestedComponent21 {
    build() {
        Column() {
            NestedComponent22()
            NestedComponent22()
        }
    }
}
