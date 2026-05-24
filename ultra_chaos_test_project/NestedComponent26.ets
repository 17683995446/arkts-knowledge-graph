/**
 * 嵌套组件文件 - 深度 26
 */

import { NestedComponent27 } from './NestedComponent27';

@Component
export struct NestedComponent26 {
    build() {
        Column() {
            NestedComponent27()
            NestedComponent27()
        }
    }
}
