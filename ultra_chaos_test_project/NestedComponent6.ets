/**
 * 嵌套组件文件 - 深度 6
 */

import { NestedComponent7 } from './NestedComponent7';

@Component
export struct NestedComponent6 {
    build() {
        Column() {
            NestedComponent7()
            NestedComponent7()
        }
    }
}
