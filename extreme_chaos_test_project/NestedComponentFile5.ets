/**
 * 嵌套组件文件 - 深度 5
 */

import { NestedComponent6 } from './NestedComponentFile6';

@Component
export struct NestedComponent5 {

    build() {
        Column() {
            NestedComponent6()
            NestedComponent6()
            NestedComponent6()
        }
    }

}
