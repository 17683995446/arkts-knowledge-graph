/**
 * 嵌套组件文件 - 深度 10
 */

import { NestedComponent11 } from './NestedComponent11';

@Component
export struct NestedComponent10 {
    build() {
        Column() {
            NestedComponent11()
            NestedComponent11()
        }
    }
}
